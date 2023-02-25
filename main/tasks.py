from django.core.validators import URLValidator
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from yaml import load as load_yaml, Loader
from requests import get
from .models import Shop, Product, Category, Parameter, ProductParameter
from celery import shared_task

@shared_task()
def partner_update_task(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

    if request.user.type != 'shop':
        return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

    url = request.data.get('url')
    if url:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)})
        else:
            stream = get(url).content

            data = load_yaml(stream, Loader=Loader)

            shop, _ = Shop.objects.get_or_create(name=data['shop'], user=request.user, url=url)

            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()
            Product.objects.filter(shop=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'],
                                                           category_id=item['category'],
                                                           model=item['model'],
                                                           price=item['price'],
                                                           price_rrc=item['price_rrc'],
                                                           quantity=item['quantity'],
                                                           is_active=True,
                                                           shop=shop
                                                           )
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.get_or_create(product=product,
                                                           parameter=parameter_object,
                                                           value=value)

            return JsonResponse({'Status': True, 'Message': 'Прайс-лист обновлен'})

    return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})