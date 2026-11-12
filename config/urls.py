

from django.contrib import admin
from django.urls import path

from comun.views import SaludView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

handler404 = "comun.errores.no_encontrado"
handler500 = "comun.errores.error_interno"
