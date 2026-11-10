

from django.contrib import admin
from django.urls import path

from comun.views import SaludView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
]

handler404 = "comun.errores.no_encontrado"
handler500 = "comun.errores.error_interno"
