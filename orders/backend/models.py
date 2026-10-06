from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings



STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)


USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)


class UserManager(BaseUserManager):
    """
    Менеджер пользователей
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Пользователь системы
    """

    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'

    objects = UserManager()

    email = models.EmailField(
        _('email address'),
        unique=True
    )

    company = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Компания'
    )

    position = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Должность'
    )

    type = models.CharField(
        max_length=5,
        choices=USER_TYPE_CHOICES,
        default='buyer',
        verbose_name='Тип пользователя'
    )

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        blank=True,
        validators=[username_validator]
    )

    is_active = models.BooleanField(
        default=False,
        verbose_name='Активен'
    )

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Shop(models.Model):
    """
    Магазин / поставщик
    """

    name = models.CharField(
        max_length=100,
        verbose_name='Название магазина'
    )

    url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка'
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shop',
        verbose_name='Пользователь'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'


class Category(models.Model):
    """
    Категория товара
    """

    shops = models.ManyToManyField(
        Shop,
        related_name='categories',
        verbose_name='Магазины'
    )

    name = models.CharField(
        max_length=100,
        verbose_name='Название категории'
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Товар
    """

    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name='Категория'
    )

    name = models.CharField(
        max_length=200,
        verbose_name='Название товара'
    )

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """
    Информация о товаре у конкретного поставщика
    """

    product = models.ForeignKey(
        Product,
        related_name='product_infos',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )

    shop = models.ForeignKey(
        Shop,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name='Магазин'
    )

    external_id = models.PositiveIntegerField(
        verbose_name='Внешний ID товара'
    )

    model = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Модель'
    )

    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )

    quantity = models.PositiveIntegerField(
        verbose_name='Количество'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )

    price_rrc = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Розничная цена'
    )

    def __str__(self):
        return self.name


class Parameter(models.Model):
    """
    Характеристика товара
    """

    name = models.CharField(
        max_length=100,
        verbose_name='Название параметра'
    )

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """
    Значение характеристики товара
    """

    product_info = models.ForeignKey(
        ProductInfo,
        related_name='parameters',
        on_delete=models.CASCADE,
        verbose_name='Информация о товаре'
    )

    parameter = models.ForeignKey(
        Parameter,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name='Параметр'
    )

    value = models.CharField(
        max_length=100,
        verbose_name='Значение'
    )

    def __str__(self):
        return f'{self.parameter}: {self.value}'


class Order(models.Model):
    """
    Заказ
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orders',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )

    dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата заказа'
    )

    status = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='basket',
        verbose_name='Статус'
    )

    def __str__(self):
        return f'Заказ №{self.id}'


class OrderItem(models.Model):
    """
    Товар в заказе
    """

    order = models.ForeignKey(
        Order,
        related_name='ordered_items',
        on_delete=models.CASCADE,
        verbose_name='Заказ'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        verbose_name='Магазин'
    )

    quantity = models.PositiveIntegerField(
        verbose_name='Количество'
    )

    def __str__(self):
        return self.product.name


class Contact(models.Model):
    """
    Контактные данные пользователя
    """

    type = models.CharField(
        max_length=20,
        verbose_name='Тип контакта'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='contacts',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )

    value = models.CharField(
        max_length=200,
        verbose_name='Значение'
    )

    def __str__(self):
        return self.value