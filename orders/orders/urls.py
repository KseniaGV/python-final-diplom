from django.contrib import admin
from django.urls import path

from backend.views import (
    PartnerUpdate,
    UserRegister,
    UserLogin,
    ConfirmAccount,
    ProductList,
    ProductDetail,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('partner/update/', PartnerUpdate.as_view()),
    path('user/register/', UserRegister.as_view()),
    path('user/login/', UserLogin.as_view()),
    path('user/register/confirm/', ConfirmAccount.as_view()),
    path('products/', ProductList.as_view()),
    path('products/<int:product_info_id>/', ProductDetail.as_view()),
]
