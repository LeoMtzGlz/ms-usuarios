from django.contrib import admin
from django.urls import path, include
from comun.views import SaludView
# Importación de Swagger (Compañero)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
    
    # Rutas de documentación (Compañero)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Tus rutas de usuarios
    path('api/v1/', include('usuarios.urls')),
]

# Handler para errores 404 (Compañero)
handler404 = "comun.errores.no_encontrado"