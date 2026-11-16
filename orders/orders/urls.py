from django.contrib import admin
from django.urls import path

from backend.views import (
    PartnerUpdate,
    UserRegister,
    UserLogin,
    ConfirmAccount,
    ProductList,
    ProductDetail,
    BasketView,
    BasketAdd,
    BasketRemove,
    BasketUpdate,
    ContactView,
    ContactAdd,
    ContactRemove,
    OrderCreate,
    OrderView,
    OrderStatusUpdate,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('partner/update/', PartnerUpdate.as_view()),
    path('user/register/', UserRegister.as_view()),
    path('user/login/', UserLogin.as_view()),
    path('user/register/confirm/', ConfirmAccount.as_view()),
    path('products/', ProductList.as_view()),
    path('products/<int:product_info_id>/', ProductDetail.as_view()),
    path('basket/', BasketView.as_view()),
    path('basket/add/', BasketAdd.as_view()),
    path('basket/remove/<int:item_id>/', BasketRemove.as_view()),
    path('basket/update/<int:item_id>/', BasketUpdate.as_view()),
    path('contacts/', ContactView.as_view()),
    path('contacts/add/', ContactAdd.as_view()),
    path('contacts/remove/<int:contact_id>/', ContactRemove.as_view()),
    path('orders/create/', OrderCreate.as_view()),
    path('orders/', OrderView.as_view()),
    path('orders/<int:order_id>/status/', OrderStatusUpdate.as_view(), name='order-status-update'),
]
