"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import (
    AceptarPrivacidadView,
    ActivarCuentaView,
    CambiarPasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,  # t-07/st-90
    PrivacidadInfoView,
    LogoutTodoView,  # HU-09 / ST-98
    RegistroView,
)
from usuarios.reenvio import ReenviarCodigoView  # t-04/st-75
from usuarios.restablecer import RestablecerPasswordView  # t-10/st-108
from usuarios.views_2fa import Activar2FAView, Confirmar2FAView  # t-30/st-206
from usuarios.views_eliminacion import EliminarCuentaView  # t-23/st-174
from usuarios.views_2fa_desactivar import Desactivar2FAView  # t-32/st-215
from usuarios.views_accesos import HistorialAccesosView  # t-22/st-168
<<<<<<< HEAD
from usuarios.views_google import LoginGoogleView  # t-33/st-219
from usuarios.reenvio import ReenviarCodigoView # t-04/st-75


from usuarios.views_recuperacion import SolicitarRecuperacionView # t-10/st-107
from usuarios.restablecer import RestablecerPasswordView # t-10/st-108
=======
from usuarios.views_perfil import PerfilView  # t-21/st-163
from usuarios.views_recuperacion import SolicitarRecuperacionView  # t-10/st-107
>>>>>>> 246981a4fa6e916a452b081203851b4f464d0ae5

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("activar/", ActivarCuentaView.as_view(), name="activar"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/renovar/", CustomTokenRefreshView.as_view(), name="token_renovar"),
    # t-33/st-219
    path("google/", LoginGoogleView.as_view(), name="login-google"),
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
    # t-23/st-174
    path("eliminar-cuenta/", EliminarCuentaView.as_view(), name="eliminar-cuenta"),
    # t-21/st-163 (HU-21 / ST-163)
    path("perfil/", PerfilView.as_view(), name="perfil"),
    # t-22/st-168
    path("accesos/", HistorialAccesosView.as_view(), name="historial-accesos"),
    # HU-09 / ST-98
    path("logout-todo/", LogoutTodoView.as_view(), name="logout-todo"),
    # t-04/st-75
    path("reenviar-codigo/", ReenviarCodigoView.as_view(), name="reenviar-codigo"),
    # t-10/st-107
    path("recuperar/", SolicitarRecuperacionView.as_view(), name="recuperar"),
    # t-10/st-108
    path("restablecer/", RestablecerPasswordView.as_view(), name="restablecer-password"),
]
