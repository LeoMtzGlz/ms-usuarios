"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import (
    AceptarPrivacidadView,
    ActivarCuentaView,
    CambiarPasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,  # t-07/st-90
    LlavePublicaView,
    PrivacidadInfoView,
    RegistroView,
)
from usuarios.views_2fa import Activar2FAView, Confirmar2FAView  # t-30/st-206
from usuarios.views_2fa_desactivar import Desactivar2FAView  # t-32/st-215
from usuarios.views_accesos import HistorialAccesosView  # t-22/st-168
from usuarios.reenvio import ReenviarCodigoView  # t-04/st-75

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("activar/", ActivarCuentaView.as_view(), name="activar"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/renovar/", CustomTokenRefreshView.as_view(), name="token_renovar"),
    path("llave-publica/", LlavePublicaView.as_view(), name="llave-publica"),  # t-14/st-135
    # t-30/st-206
    path("2fa/activar/", Activar2FAView.as_view(), name="2fa-activar"),
    path("2fa/confirmar/", Confirmar2FAView.as_view(), name="2fa-confirmar"),
    # t-32/st-215
    path("2fa/desactivar/", Desactivar2FAView.as_view(), name="2fa-desactivar"),
    # t-29/st-201
    path("privacidad/", PrivacidadInfoView.as_view(), name="privacidad-info"),
    path("privacidad/aceptar/", AceptarPrivacidadView.as_view(), name="privacidad-aceptar"),
    # HU-11 / ST-112
    path("cambiar-password/", CambiarPasswordView.as_view(), name="cambiar-password"),
    # t-22/st-168
    path("accesos/", HistorialAccesosView.as_view(), name="historial-accesos"),
    # t-04/st-75
    path("reenviar-codigo/", ReenviarCodigoView.as_view(), name="reenviar-codigo"),
]
