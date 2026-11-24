"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import (
    AceptarPrivacidadView,
    ActivarCuentaView,
    CambiarPasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView, # t-07/st-90
    PrivacidadInfoView,
    RegistroView,
)
from usuarios.views_2fa import Activar2FAView, Confirmar2FAView  # t-30/st-206

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("activar/", ActivarCuentaView.as_view(), name="activar"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("login/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    # t-30/st-206
    path("2fa/activar/", Activar2FAView.as_view(), name="2fa-activar"),
    path("2fa/confirmar/", Confirmar2FAView.as_view(), name="2fa-confirmar"),
    # t-29/st-201
    path("privacidad/", PrivacidadInfoView.as_view(), name="privacidad-info"),
    path("privacidad/aceptar/", AceptarPrivacidadView.as_view(), name="privacidad-aceptar"),
    # HU-11 / ST-112
    path("cambiar-password/", CambiarPasswordView.as_view(), name="cambiar-password"),
]