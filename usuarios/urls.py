"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import (
    RegistroView,
    CustomTokenObtainPairView,
    PrivacidadInfoView,
    AceptarPrivacidadView,
    CambiarPasswordView,
)
from usuarios.views_2fa import Activar2FAView, Confirmar2FAView  # t-30/st-206
from usuarios.views_perfil import PerfilView

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    
    # t-30/st-206
    path("2fa/activar/", Activar2FAView.as_view(), name="2fa-activar"),
    path("2fa/confirmar/", Confirmar2FAView.as_view(), name="2fa-confirmar"),
    
    # t-29/st-201
    path("privacidad/", PrivacidadInfoView.as_view(), name="privacidad-info"),
    path("privacidad/aceptar/", AceptarPrivacidadView.as_view(), name="privacidad-aceptar"),

    # HU-11 / ST-112
    path("cambiar-password/", CambiarPasswordView.as_view(), name="cambiar-password"),

    # HU-21 / ST-163
    path("perfil/", PerfilView.as_view(), name="perfil"),

]
