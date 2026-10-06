import yaml
import requests

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import JsonResponse

from rest_framework.views import APIView

from .models import (
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter,
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
            response = requests.get(url)
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
