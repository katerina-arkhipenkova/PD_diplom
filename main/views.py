from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q, Sum, F
from requests import get
from distutils.util import strtobool
from yaml import load as load_yaml, Loader
from ujson import loads as load_json
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ShopSerializer, UserSerializer, ContactSerializer, CategorySerializer, ProductSerializer, \
    OrderItemSerializer, OrderSerializer
from .models import Shop, Product, Category, Parameter, ProductParameter, User, ConfirmEmailToken, Contact, Order, \
    OrderItem
from main.tasks import partner_update_task


class RegisterAccountAPIView(APIView):
    '''
    Регистрация покупателя
    '''

    def post(self, request, *args, **kwargs):
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            user.set_password(request.data['password'])
            user.save()
            token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
            return Response(
                {'status': True, 'token for confirm email': token.key, 'user': user.email, 'password': user.password})
        else:
            return Response({'status': False, 'error': user_serializer.errors},
                            status=status.HTTP_403_FORBIDDEN)


class ConfirmAccountAPIView(APIView):
    """
    Подтверждение регистрации
    """

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return Response({'Status': True})
            else:
                return Response({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class LoginUserAPIView(APIView):
    '''
    Авторизация
    '''

    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return Response({'status': True, 'token': token.key, 'user': user.email})

            return Response({'status': False, 'error': 'Не удалось войти'}, status=status.HTTP_403_FORBIDDEN)

        return Response({'status': False, 'error': 'Не указаны необходимые поля'},
                        status=status.HTTP_400_BAD_REQUEST)


class PasswordResetAPIView(APIView):
    '''
    Запрос на изменение пароля
    '''

    def post(self, request, *args, **kwargs):
        if {'email'}.issubset(request.data):
            user = User.objects.get(email=request.data['email'])
            token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
            return Response({'status': True, 'token for confirm email': token.key, 'user': user.email})
        else:
            return Response({'status': False, 'error': 'Необходимо указать email'},
                            status=status.HTTP_403_FORBIDDEN)


class PasswordResetConfirmAPIView(APIView):
    '''
    Подтверждение смены пароля
    '''

    def post(self, request, *args, **kwargs):
        if {'email', 'token', 'password'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.set_password(request.data['password'])
                token.user.save()
                token.delete()
                return Response({'Status': True, 'Token': token.user.token})
            else:
                return Response({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class UserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if 'password' not in request.data:
            if serializer.is_valid():
                serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            else:
                return Response({'status': False, 'error': serializer.errors},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Для изменения пароля воспользуйтесь формой "Сменить пароль"'},
                            status=status.HTTP_403_FORBIDDEN)


class ContactAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {'city', 'street', 'phone'}.issubset(request.data):
            # request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            else:
                return Response({'status': False, 'error': serializer.errors},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Необходимо указать поля  "city", "street", "phone"'},
                            status=status.HTTP_403_FORBIDDEN)

    def put(self, request, *args, **kwargs):
        if {'id'}.issubset(request.data):
            contact = Contact.objects.get(pk=int(request.data['id']))
            serializer = ContactSerializer(contact, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            else:
                return Response({'status': False, 'error': serializer.errors},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Необходимо указать id контакта'},
                            status=status.HTTP_403_FORBIDDEN)

    def delete(self, request, *args, **kwargs):
        if {'items'}.issubset(request.data):
            for id in request.data['items'].split(','):
                if Contact.objects.filter(pk=int(id)).exists():
                    contact = Contact.objects.get(pk=int(id))
                    contact.delete()
            return Response({'status': True}, status=status.HTTP_200_OK)
        else:
            return Response({'status': False, 'error': 'Необходимо указать id контакта'},
                            status=status.HTTP_403_FORBIDDEN)


class ShopAPIView(APIView):
    def get(self, request, *args, **kwargs):
        shops = Shop.objects.filter(state=True)
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data)


class CategoryAPIView(APIView):
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class PartnerUpdateAPIView(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'change_price'

    def post(self, request, *args, **kwargs):
        """
        Вызываем функцию из celery
        """
        partner_update_task.delay(request.data, request.user, *args, **kwargs)
        # # Старый вариант без Celery
        # if not request.user.is_authenticated:
        #     return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        #
        # if request.user.type != 'shop':
        #     return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        #
        # url = request.data.get('url')
        # if url:
        #     validate_url = URLValidator()
        #     try:
        #         validate_url(url)
        #     except ValidationError as e:
        #         return JsonResponse({'Status': False, 'Error': str(e)})
        #     else:
        #         stream = get(url).content
        #
        #         data = load_yaml(stream, Loader=Loader)
        #
        #         shop, _ = Shop.objects.get_or_create(name=data['shop'], user=request.user, url=url)
        #
        #         for category in data['categories']:
        #             category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
        #             category_object.shops.add(shop.id)
        #             category_object.save()
        #         Product.objects.filter(shop=shop.id).delete()
        #         for item in data['goods']:
        #             product, _ = Product.objects.get_or_create(name=item['name'],
        #                                                        category_id=item['category'],
        #                                                        model=item['model'],
        #                                                        price=item['price'],
        #                                                        price_rrc=item['price_rrc'],
        #                                                        quantity=item['quantity'],
        #                                                        is_active=True,
        #                                                        shop=shop
        #                                                        )
        #             for name, value in item['parameters'].items():
        #                 parameter_object, _ = Parameter.objects.get_or_create(name=name)
        #                 ProductParameter.objects.get_or_create(product=product,
        #                                                        parameter=parameter_object,
        #                                                        value=value)
        #
        #         return JsonResponse({'Status': True, 'Message': 'Прайс-лист обновлен'})
        #
        # return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerStateAPIView(APIView):
    """
    Класс для статуса заказов

    """
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        state = request.data.get('state')

        if state:
            try:
                Shop.objects.filter(user=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True, 'Message': f'Статус магазина изменен на {state}'})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product__shop__user_id=request.user.id).exclude(order_state='basket').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product__price_rrc'))).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ProductAPIView(APIView):
    '''
    Просмотр товаров
    '''

    def get(self, request, *args, **kwargs):
        query = Q(is_active=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(category_id=category_id)

        queryset = Product.objects.filter(
            query).select_related(
            'shop', 'category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        basket = Order.objects.filter(
            ordered_items__product__shop__user_id=request.user.id).exclude(order_state='basket').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product__price_rrc'))).distinct()
        # basket = Order.objects.filter(
        #     user_id=request.user.id, order_state='basket')
        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {'items'}.issubset(request.data):
            items = load_json(request.data.get('items'))
            order, _ = Order.objects.get_or_create(user=request.user, order_state='basket')
            for order_item in items:
                order_item.update({'order': order.id})
                serializer = OrderItemSerializer(data=order_item)
                product = Product.objects.filter(id=order_item['product']).values('quantity')
                print(order_item)
                if product:
                    if product[0]['quantity'] >= order_item['quantity']:
                        if serializer.is_valid():
                            serializer.save()
                        else:
                            return Response({'status': False, 'error': serializer.errors},
                                            status=status.HTTP_403_FORBIDDEN)
                    else:
                        return Response({'status': False, 'error': 'Такого количества товаров нет в наличии'},
                                        status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({'status': False, 'error': 'Такого товара нет в наличии'},
                                    status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Необходимо указать поля "items"'},
                            status=status.HTTP_403_FORBIDDEN)

        return Response({"status": True})

    def put(self, request, *args, **kwargs):
        if {'items'}.issubset(request.data):
            items = load_json(request.data.get('items'))
            order, _ = Order.objects.get_or_create(user=request.user, order_state='basket')
            for order_item in items:
                product = Product.objects.filter(id=order_item['product']).values('quantity')
                if product[0]['quantity'] >= order_item['quantity']:
                    OrderItem.objects.filter(order=order.id, product=order_item['product']) \
                        .update(quantity=order_item['quantity'])
                else:
                    return Response({'status': False, 'error': 'Такого количества товаров нет в наличии'},
                                    status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Необходимо указать поля "items"'},
                            status=status.HTTP_403_FORBIDDEN)

        return Response({"status": True})

    def delete(self, request, *args, **kwargs):
        if {'items'}.issubset(request.data):
            for id in request.data['items'].split(','):
                if OrderItem.objects.filter(pk=int(id)).exists():
                    order_item = OrderItem.objects.get(pk=int(id))
                    order_item.delete()
                    return Response({'status': True}, status=status.HTTP_200_OK)
                else:
                    return Response({'status': False, 'error': 'Такой позиции нет в корзине'},
                                    status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'status': False, 'error': 'Необходимо указать id позиции'},
                            status=status.HTTP_403_FORBIDDEN)


class OrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        order = Order.objects.filter(
            ordered_items__product__shop__user_id=request.user.id).exclude(order_state='new').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product__price_rrc'))).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {'id', 'contact'}.issubset(request.data):
            order = Order.objects.filter(pk=int(request.data['id'])).update(contact=int(request.data['contact']),
                                                                            order_state='new')
            user_email = request.user.email
            user_message = f'Номер вашего заказа {order}'
            send_mail('Заказ в интернет-магазине', user_message, settings.EMAIL_HOST_USER, [user_email])
            partner_message = f'Пользователь {user_email} разместил заказ №{order}'
            send_mail(f'Новый заказ {order}', partner_message, settings.EMAIL_HOST_USER, settings.RECIPIENTS_EMAIL)
        else:
            return Response({'status': False, 'error': 'Необходимо указать id и contact'},
                            status=status.HTTP_403_FORBIDDEN)

        return Response({'status': True, 'message': f'Заказ номер {order} создан!'})
