from django.conf.urls import static
from django.contrib import admin
from config import settings

from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("api/driver/", include("drivers.urls", namespace="drivers")),
]
