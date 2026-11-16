import yaml
import requests

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from .serializers import ProductInfoSerializer

from .models import (
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter,
    User,
    ConfirmEmailToken,
    Order,
    OrderItem,
    Contact
)


class PartnerUpdate(APIView):
    """
    Обновление прайса магазина
    """

    def post(self, request, *args, **kwargs):

        # Проверяем авторизацию
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    'Status': False,
                    'Error': 'Log in required'
                },
                status=403
            )

        # Проверяем, является ли ползователь опставщиком
        if request.user.type != 'shop':
            return JsonResponse(
                {
                    'Status': False,
                    'Error': 'Только для магазинов'
                },
                status=403
            )

        # Получаем ссылку на YAML-файл
        url = request.data.get('url')

        if not url:
            return JsonResponse(
                {
                    'Status': False,
                    'Errors': 'Не указана ссылка на файл'
                },
                status=400
            )

        # Проверяем корректность URL
        validate_url = URLValidator()

        try:
            validate_url(url)
        except ValidationError:
            return JsonResponse(
                {
                    'Status': False,
                    'Error': 'Некорректная ссылка'
                },
                status=400
            )

        # Загружаем YAML-файл
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            return JsonResponse(
                {
                    'Status': False,
                    'Error': f'Ошибка загрузки файла: {error}'
                },
                status=400
            )

        # Читаем YAML
        try:
            data = yaml.safe_load(response.content)
        except yaml.YAMLError:
            return JsonResponse(
                {
                    'Status': False,
                    'Error': 'Ошибка чтения YAML-файла'
                },
                status=400
            )

        # Получаем или создаём магазин
        shop, _ = Shop.objects.update_or_create(
            user=request.user,
            defaults={
                'name': data['shop'],
                'url': url,
            }
        )

        # Загружаем категории
        for category in data['categories']:
            category_object, _ = Category.objects.update_or_create(
                id=category['id'],
                defaults={
                    'name': category['name']
                }
            )

            category_object.shops.add(shop)

        # Удаляем старый прайс этого магазина
        ProductInfo.objects.filter(shop=shop).delete()

        # Загружаем товары
        for item in data['goods']:

            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category']
            )

            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                external_id=item['id'],
                model=item.get('model', ''),
                name=item['name'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
            )

            # Загружаем характеристики товара
            for name, value in item.get('parameters', {}).items():

                parameter_object, _ = Parameter.objects.get_or_create(
                    name=name
                )

                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter_object,
                    value=value,
                )

        return JsonResponse(
            {
                'Status': True
            }
        )

class UserRegister(APIView):
    """
    Регистрация нового пользователя с подтверждением email.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        # Проверяем обязательные поля
        if not email or not password:
            return Response(
                {
                    'Status': False,
                    'Error': 'Необходимо указать email и пароль'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, зарегистрирован ли пользователь
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {
                    'Status': False,
                    'Error': 'Пользователь с таким email уже существует'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаём неактивного пользователя
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            type='buyer',
            is_active=False
        )

        # Создаём токен подтверждения
        token = ConfirmEmailToken.objects.create(user=user)

        # Отправляем письмо
        send_mail(
            subject='Подтверждение регистрации',
            message=(
                f'Здравствуйте, {first_name}!\n\n'
                'Для подтверждения регистрации используйте токен:\n'
                f'{token.key}\n\n'
                'Передайте при подтверждении регистрации.'
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False
        )

        return Response(
            {
                'Status': True,
                'Message': 'Пользователь создан. Проверьте email для подтверждения регистрации.'
            },
            status=status.HTTP_201_CREATED
        )

class ConfirmAccount(APIView):
    """
    Подтверждение регистрации пользователя по email и токену.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        key = request.data.get('token')

        if not email or not key:
            return Response(
                {
                    'Status': False,
                    'Error': 'Необходимо указать email и токен'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ищем токен нужного пользователя
        token = ConfirmEmailToken.objects.select_related('user').filter(
            user__email__iexact=email,
            key=key
        ).first()

        if token is None:
            return Response(
                {
                    'Status': False,
                    'Error': 'Неверный email или токен'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Активируем пользователя
        user = token.user
        user.is_active = True
        user.save(update_fields=['is_active'])

        # Удаляем использованный токен
        token.delete()

        return Response(
            {
                'Status': True,
                'Message': 'Email успешно подтверждён'
            },
            status=status.HTTP_200_OK
        )

class UserLogin(APIView):
    """
    Авторизация пользователя
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {
                    'Status': False,
                    'Error': 'Необходимо указать email и пароль',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request=request,
            email=email,
            password=password,
        )

        if user is None:
            return Response(
                {
                    'Status': False,
                    'Error': 'Неверный email или пароль',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                'Status': True,
                'Token': token.key,
            },
            status=status.HTTP_200_OK,
        )
class ProductList(APIView):
    """
    Получение списка товаров с поиском и фильтрацией
    """
    permission_classes = [AllowAny]

    def get(self, request):
        products = ProductInfo.objects.select_related(
            'product',
            'product__category',
            'shop'
        ).prefetch_related('parameters__parameter').all()

        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')
        search = request.query_params.get('search')

        if shop_id:
            products = products.filter(shop_id=shop_id)

        if category_id:
            products = products.filter(product__category_id=category_id)

        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(model__icontains=search) |
                Q(product__name__icontains=search) |
                Q(shop__name__icontains=search)
            )

        serializer = ProductInfoSerializer(products, many=True)

        return Response(serializer.data)


class ProductDetail(APIView):

    """
    Получение подробной информации об отдельном товаре
    """
    permission_classes = [AllowAny]

    def get(self, request, product_info_id):
        product = get_object_or_404(
            ProductInfo.objects.select_related(
                'product',
                'product__category',
                'shop'
            ).prefetch_related('parameters__parameter'),
            id=product_info_id
        )

        serializer = ProductInfoSerializer(product)

        return Response(serializer.data)

class BasketView(APIView):
    """
    Просмотр корзины покупателя
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        basket, created = Order.objects.get_or_create(
            user=request.user,
            status='basket'
        )

        items = basket.ordered_items.select_related(
            'product',
            'shop'
        )

        basket_items = []
        total_sum = 0

        for item in items:
            price = item.price
            total = price * item.quantity
            total_sum += total

            basket_items.append({
                'id': item.id,
                'product': item.product.name,
                'shop': item.shop.name,
                'quantity': item.quantity,
                'price': price,
                'total': total,
            })

        return Response({
            'id': basket.id,
            'items': basket_items,
            'total_sum': total_sum,
        })


class BasketAdd(APIView):

    """
    Добавление товара в корзину покупателя
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity', 1)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {'Status': False, 'Error': 'Некорректное количество'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {'Status': False, 'Error': 'Количество должно быть больше нуля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product_info = get_object_or_404(
            ProductInfo,
            id=product_info_id
        )

        if quantity > product_info.quantity:
            return Response(
                {'Status': False, 'Error': 'Недостаточно товара на складе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        basket, created = Order.objects.get_or_create(
            user=request.user,
            status='basket'
        )

        item, created = OrderItem.objects.get_or_create(
            order=basket,
            product=product_info.product,
            shop=product_info.shop,
            defaults={
                'quantity': quantity,
                'price': product_info.price
            }
        )

        if not created:
            new_quantity = item.quantity + quantity

            if new_quantity > product_info.quantity:
                return Response(
                    {'Status': False, 'Error': 'Недостаточно товара на складе'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = new_quantity
            item.price = product_info.price
            item.save()

        return Response({
            'Status': True,
            'Message': 'Товар добавлен в корзину'
        }, status=status.HTTP_201_CREATED)


class BasketRemove(APIView):

    """
    Удаление товара из корзины покупателя
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        item = get_object_or_404(
            OrderItem,
            id=item_id,
            order__user=request.user,
            order__status='basket'
        )

        item.delete()

        return Response({
            'Status': True,
            'Message': 'Товар удалён из корзины'
        })


class BasketUpdate(APIView):

    """
    Изменение количества товара в корзине покупателя
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        item = get_object_or_404(
            OrderItem,
            id=item_id,
            order__user=request.user,
            order__status='basket'
        )

        try:
            quantity = int(request.data.get('quantity'))
        except (TypeError, ValueError):
            return Response(
                {'Status': False, 'Error': 'Некорректное количество'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {'Status': False, 'Error': 'Количество должно быть больше нуля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product_info = get_object_or_404(
            ProductInfo,
            product=item.product,
            shop=item.shop
        )

        if quantity > product_info.quantity:
            return Response(
                {'Status': False, 'Error': 'Недостаточно товара на складе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = quantity
        item.save(update_fields=['quantity'])

        return Response({
            'Status': True,
            'Message': 'Количество товара обновлено'
        })

class ContactView(APIView):

    """
    Просмотр контактных данных покупателя
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)

        result = []

        for contact in contacts:
            result.append({
                'id': contact.id,
                'type': contact.type,
                'value': contact.value,
            })

        return Response(result)


class ContactAdd(APIView):

    """
    Добавление контактных данных покупателя
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_type = request.data.get('type')
        value = request.data.get('value')

        if not contact_type or not value:
            return Response(
                {'Status': False, 'Error': 'Необходимо указать тип и значение контакта'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if contact_type not in ['phone', 'address']:
            return Response(
                {'Status': False, 'Error': 'Тип контакта должен быть phone или address'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contacts_count = Contact.objects.filter(
            user=request.user,
            type=contact_type
        ).count()

        if contact_type == 'phone' and contacts_count >= 1:
            return Response(
                {'Status': False, 'Error': 'Можно добавить только один номер телефона'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if contact_type == 'address' and contacts_count >= 5:
            return Response(
                {'Status': False, 'Error': 'Можно добавить не более пяти адресов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact = Contact.objects.create(
            user=request.user,
            type=contact_type,
            value=value
        )

        return Response({
            'Status': True,
            'id': contact.id,
            'Message': 'Контакт успешно добавлен'
        }, status=status.HTTP_201_CREATED)


class ContactRemove(APIView):

    """
    Удаление контактных данных покупателя
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, contact_id):
        contact = get_object_or_404(
            Contact,
            id=contact_id,
            user=request.user
        )

        contact.delete()

        return Response({
            'Status': True,
            'Message': 'Контакт успешно удалён'
        })

class OrderCreate(APIView):

    """
    Оформление заказа покупателем
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        if request.user.type != 'buyer':
            return Response(
                {
                    'Status': False,
                    'Error': 'Оформлять заказы могут только покупатели'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        contact_id = request.data.get('contact_id')

        contact = get_object_or_404(
            Contact,
            id=contact_id,
            user=request.user
        )

        basket = Order.objects.filter(
            user=request.user,
            status='basket'
        ).first()

        if not basket or not basket.ordered_items.exists():
            return Response(
                {'Status': False, 'Error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in basket.ordered_items.all():
            product_info = ProductInfo.objects.filter(
                product=item.product,
                shop=item.shop
            ).first()

            if not product_info or item.quantity > product_info.quantity:
                return Response(
                    {
                        'Status': False,
                        'Error': f'Недостаточно товара: {item.product.name}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        basket.contact = contact
        basket.status = 'new'
        basket.save(update_fields=['contact', 'status'])

        # Отправляем письмо покупателю
        send_mail(
            subject='Ваш заказ успешно оформлен',
            message=(
                f'Здравствуйте, {request.user.first_name}!\n\n'
                f'Ваш заказ №{basket.id} успешно оформлен.\n'
                'Статус заказа: Новый.'
            ),
            from_email=None,
            recipient_list=[request.user.email],
            fail_silently=False
        )

        # Отправляем письмо администратору
        send_mail(
            subject=f'Новый заказ №{basket.id}',
            message=(
                f'Поступил новый заказ №{basket.id}.\n'
                f'Покупатель: {request.user.email}\n'
                f'Контакт доставки: {contact.value}'
            ),
            from_email=None,
            recipient_list=[email for name, email in settings.ADMINS],
            fail_silently=False
        )

        return Response({
            'Status': True,
            'Message': 'Заказ успешно оформлен',
            'Order_id': basket.id
        }, status=status.HTTP_201_CREATED)


# Просмотр истории заказов покупателя
class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).exclude(status='basket').prefetch_related(
            'ordered_items__product'
        )

        result = []

        for order in orders:
            items = []

            for item in order.ordered_items.all():
                items.append({
                    'product': item.product.name,
                    'quantity': item.quantity,
                })

            result.append({
                'id': order.id,
                'status': order.status,
                'contact': order.contact.value if order.contact else None,
                'items': items,
            })

        return Response(result)

class OrderStatusUpdate(APIView):

    """
    Изменение статуса заказа поставщиком
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        if request.user.type != 'shop':
            return Response(
                {'Status': False, 'Error': 'Доступ разрешён только поставщикам'},
                status=status.HTTP_403_FORBIDDEN
            )

        order = get_object_or_404(
            Order,
            id=order_id,
            ordered_items__shop__user=request.user
        )

        new_status = request.data.get('status')

        valid_statuses = [
            choice[0]
            for choice in Order._meta.get_field('status').choices
        ]

        if new_status not in valid_statuses or new_status == 'basket':
            return Response(
                {'Status': False, 'Error': 'Некорректный статус заказа'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save(update_fields=['status'])

        return Response({
            'Status': True,
            'Message': 'Статус заказа обновлён',
            'Order_id': order.id,
            'New_status': order.status
        })