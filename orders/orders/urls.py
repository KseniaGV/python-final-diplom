from django.contrib import admin
from django.urls import path

from backend.views import PartnerUpdate


urlpatterns = [
    path('admin/', admin.site.urls),
    path('partner/update/', PartnerUpdate.as_view()),
]
