from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import RegisterAccountAPIView, PartnerUpdateAPIView, PartnerStateAPIView, UserAPIView, ConfirmAccountAPIView, LoginUserAPIView, \
    ContactAPIView, PasswordResetAPIView, PasswordResetConfirmAPIView, ShopViewSet, CategoryViewSet, ProductAPIView, BasketAPIView, \
    OrderAPIView, PartnerOrderAPIView


app_name = 'main'

router = DefaultRouter()
router.register('shops', ShopViewSet)
router.register('categories', CategoryViewSet)

urlpatterns = [
    path('user/registration', RegisterAccountAPIView.as_view()),
    path('user/registration/confirm', ConfirmAccountAPIView.as_view()),
    path('user/login', LoginUserAPIView.as_view()),
    path('user/contact', ContactAPIView.as_view()),
    path('user/password_reset', PasswordResetAPIView.as_view()),
    path('user/password_reset/confirm', PasswordResetConfirmAPIView.as_view()),
    # path('shops', ShopAPIView.as_view()),
    path('products', ProductAPIView.as_view()),
    # path('categories', CategoryAPIView.as_view()),
    path('basket', BasketAPIView.as_view()),
    path('order', OrderAPIView.as_view()),
    path('partner/update', PartnerUpdateAPIView.as_view()),
    path('partner/state', PartnerStateAPIView.as_view()),
    path('partner/orders', PartnerOrderAPIView.as_view()),
    path('user/details', UserAPIView.as_view())
] + router.urls