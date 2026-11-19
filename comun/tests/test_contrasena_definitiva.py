"""Pruebas de t-12/st-116 (HU-12): permiso ContrasenaDefinitiva.

Mientras el token diga debe_cambiar_password=True, cualquier endpoint con los permisos
por defecto responde 403 debe_cambiar_password. El claim lo agrega el login (HU-05,
ST-81); aquí se pone a mano en el token.
"""
import pytest
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from comun.permisos import ContrasenaDefinitiva, EsAdministrador, permisos_por_defecto_mas

pytestmark = pytest.mark.django_db


class VistaConPermisosPorDefecto(APIView):
    """Cualquier endpoint que no declare permission_classes (usa los de settings)."""

    def get(self, request):
        return Response({"ok": True})


class VistaCambiarPassword(APIView):
    """Como será cambiar-password (HU-11): solo exige sesión, sin ContrasenaDefinitiva."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"ok": True})


def _token(usuario, **claims):
    acceso = RefreshToken.for_user(usuario).access_token
    for nombre, valor in claims.items():
        acceso[nombre] = valor
    return str(acceso)


def _llamar(vista, token=None):
    encabezados = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    respuesta = vista.as_view()(APIRequestFactory().get("/api/v1/algo/", **encabezados))
    respuesta.render()
    return respuesta


def test_esta_en_los_permisos_por_defecto():
    clases = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    assert clases[0] == "rest_framework.permissions.IsAuthenticated"
    assert "comun.permisos.ContrasenaDefinitiva" in clases


def test_con_contrasena_temporal_responde_403(usuario, llaves):
    respuesta = _llamar(VistaConPermisosPorDefecto, _token(usuario, debe_cambiar_password=True))

    assert respuesta.status_code == 403
    assert respuesta.data["codigo"] == "debe_cambiar_password"
    assert respuesta.data["mensaje"] == "Debes cambiar tu contraseña temporal antes de continuar."


def test_con_contrasena_definitiva_deja_pasar(usuario, llaves):
    respuesta = _llamar(VistaConPermisosPorDefecto, _token(usuario, debe_cambiar_password=False))

    assert respuesta.status_code == 200


def test_token_sin_el_claim_deja_pasar(usuario, llaves):
    assert _llamar(VistaConPermisosPorDefecto, _token(usuario)).status_code == 200


def test_sin_token_sigue_respondiendo_401(llaves):
    respuesta = _llamar(VistaConPermisosPorDefecto)

    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


def test_cambiar_password_funciona_con_contrasena_temporal(usuario, llaves):
    respuesta = _llamar(VistaCambiarPassword, _token(usuario, debe_cambiar_password=True))

    assert respuesta.status_code == 200


def test_permisos_por_defecto_mas_incluye_contrasena_definitiva():
    clases = permisos_por_defecto_mas(EsAdministrador)

    assert ContrasenaDefinitiva in clases
    assert clases[-1] is EsAdministrador