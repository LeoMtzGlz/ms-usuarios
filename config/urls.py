

from django.contrib import admin
from django.urls import path

from comun.views import SaludView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
]
