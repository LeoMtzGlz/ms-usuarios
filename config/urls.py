

from django.contrib import admin
from django.urls import include, path

from comun.views import AuditoriaView, SaludView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
    path("api/v1/auditoria/", AuditoriaView.as_view(), name="auditoria"),  # hu-26/st-189
    path("api/v1/auth/", include("usuarios.urls")),  # hu-02/st-66
    path("api/v1/usuarios/", include("usuarios.urls_admin")),  # hu-15/st-140
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

handler404 = "comun.errores.no_encontrado"
handler500 = "comun.errores.error_interno"
