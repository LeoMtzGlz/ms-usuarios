"""Pruebas de HU-08/ST-94: cierre de sesión mediante refresh JWT."""

import pytest

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken
)
from usuarios.tokens import CustomTokenObtainPairSerializer
from datetime import timedelta

from django.utils import timezone

pytestmark = pytest.mark.django_db

URL_LOGOUT = "/api/v1/auth/logout/"
URL_RENOVAR = "/api/v1/auth/token/renovar/"

def test_logout_invalida_refresh_token(api_client, usuario, llaves):
    """Cerrar sesión debe invalidar el refresh recibido."""

    # Generar un refresh con los claims personalizados del proyecto.
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)

    # Enviar el refresh al endpoint de logout.
    respuesta = api_client.post(
        URL_LOGOUT, 
        {"refresh": str(refresh)},
        format="json"
    )

    assert respuesta.status_code == 200, respuesta.data
    assert respuesta.data["mensaje"] == "Sesión cerrada correctamente."

    # Verificar que el token fue agregado a la lista negra.
    registro = OutstandingToken.objects.get(jti=refresh["jti"])

    assert BlacklistedToken.objects.filter(token=registro).exists()

    # Un refresh revocado no debe permitir renovar la sesión.
    renovacion = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    assert renovacion.status_code == 401
    assert renovacion.json()["codigo"] == "token_invalido"


def test_logout_rechaza_refresh_invalido(api_client, llaves):
    """El logout debe rechazar un refresh token malformado."""
    respuesta = api_client.post(
        URL_LOGOUT,
        {"refresh": "token-invalido"},
        format="json",
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_refresh_vencido(api_client, usuario, llaves):
    """El logout debe rechazar un refresh token expirado."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    refresh.set_exp(
        from_time=timezone.now() - timedelta(minutes=2),
        lifetime=timedelta(minutes=1),
    )

    respuesta = api_client.post(
        URL_LOGOUT,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_refresh_revocado(api_client, usuario, llaves):
    """Un refresh previamente revocado no debe aceptarse."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    refresh.blacklist()

    respuesta = api_client.post(
        URL_LOGOUT,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_solicitud_sin_refresh(api_client, llaves):
    """El endpoint debe rechazar solicitudes sin refresh token."""
    respuesta = api_client.post(
        URL_LOGOUT,
        {},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert "refresh" in respuesta.json()["campos"]


def test_logout_funciona_con_access_vencido(api_client, usuario, llaves):
    """Debe permitir cerrar sesión aunque el access haya expirado."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    access = refresh.access_token

    access.set_exp(
        from_time=timezone.now() - timedelta(minutes=2),
        lifetime=timedelta(minutes=1),
    )

    respuesta = api_client.post(
        URL_LOGOUT,
        {"refresh": str(refresh)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    assert respuesta.status_code == 200, respuesta.data

    registro = OutstandingToken.objects.get(jti=refresh["jti"])
    assert BlacklistedToken.objects.filter(token=registro).exists()
