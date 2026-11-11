from rest_framework import serializers

from .models import (
    Product,
    ProductInfo,
    Shop,
    Category,
    ProductParameter,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)
    parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = (
            'id',
            'product',
            'shop',
            'external_id',
            'model',
            'name',
            'quantity',
            'price',
            'price_rrc',
            'parameters',
        )