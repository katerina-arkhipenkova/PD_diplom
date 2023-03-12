import pytest
from rest_framework.test import APIClient
from model_bakery import baker
from main.models import Product, Category, User


@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def product_factory():
    def factory(*args, **kwargs):
        return baker.make(Product, *args, **kwargs)

    return factory

@pytest.fixture
def category():
    return Category.objects.create(name='test_category')

@pytest.fixture
def user():
    return User.objects.create_user(email='test@test.ru', password='testpassword', is_active=True)

@pytest.fixture
def token(client):
    response = client.post('/api/v1/user/login', data={'email': 'test@test.ru', 'password': 'testpassword'})
    token = response.json()['token']
    return token

@pytest.mark.django_db
def test_product_list(client, product_factory, category):
    products = product_factory(_quantity=10, category=category)
    products.sort(key=lambda x: x.name)
    response = client.get('/api/v1/products')
    data = response.json()
    assert response.status_code == 200
    assert len(data) == len(products)
    data.sort(key=lambda x: x['name'])
    for i, product in enumerate(data):
        assert product['name'] == products[i].name

@pytest.mark.django_db
def test_user_registration(client):
    count = User.objects.count()
    response = client.post('/api/v1/user/registration', data={'email': 'test@test.ru', 'password': 'testpassword'})
    assert response.status_code == 200
    assert User.objects.count() == count + 1

@pytest.mark.django_db
def test_login_user(client, user):
    response = client.post('/api/v1/user/login', data={'email': 'test@test.ru', 'password': 'testpassword'})
    assert response.status_code == 200
    assert response.json()['user'] == 'test@test.ru'

@pytest.mark.django_db
def test_get_user_details(client, user, token):
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    response = client.get('/api/v1/user/details')
    assert response.status_code == 200
    assert response.json()['email'] == user.email

@pytest.mark.django_db
def test_create_user_contact(client, user, token):
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    response = client.post('/api/v1/user/contact', data={'city': 'test_city', 'street': 'test_street', 'house': 'test_house',
                                                         'phone': 'test_phone'})
    assert response.status_code == 200
    response = client.get('/api/v1/user/contact')
    assert response.status_code == 200
    assert response.json()[0]['city'] == 'test_city'