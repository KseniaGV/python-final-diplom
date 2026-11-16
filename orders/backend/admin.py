from django.contrib import admin
from django.core.mail import send_mail
from django.db import transaction

from .models import (
    User,
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter,
    Order,
    OrderItem,
    Contact,
)

admin.site.register(User)
admin.site.register(Shop)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductInfo)
admin.site.register(Parameter)
admin.site.register(ProductParameter)
admin.site.register(OrderItem)
admin.site.register(Contact)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'dt', 'contact')
    list_filter = ('status', 'dt')
    search_fields = ('user__email',)
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            old_status = Order.objects.get(pk=obj.pk).status

        super().save_model(request, obj, form, change)

        if change and old_status != obj.status:
            transaction.on_commit(
                lambda: send_mail(
                    subject=f'Изменение статуса заказа №{obj.id}',
                    message=(
                        f'Статус вашего заказа №{obj.id} изменён.\n'
                        f'Новый статус: {obj.get_status_display()}.'
                    ),
                    from_email=None,
                    recipient_list=[obj.user.email],
                    fail_silently=False
                )
            )


admin.site.register(Order, OrderAdmin)