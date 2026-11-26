
"""Pruebas de HU-07/ST-92: validaciones de renovación de tokens JWT."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from usuarios.tokens import CustomTokenObtainPairSerializer


pytestmark = pytest.mark.django_db

URL_RENOVAR = "/api/v1/auth/token/renovar/"


def test_rechaza_refresh_token_vencido(api_client, usuario, llaves):
    """Un refresh expirado no debe permitir renovar la sesión."""

    # Crear un refresh válido para el usuario.
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)

    # Simular que el token venció hace un minuto.
    refresh["exp"] = int(
        (timezone.now() - timedelta(minutes=1)).timestamp()
    )

    # Intentar renovar la sesión con el refresh vencido.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    # La API debe rechazar el token expirado.
    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"

    # No deben entregarse tokens nuevos.
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rechaza_access_token_como_refresh(api_client, usuario, llaves):
    """Un access token no debe servir para renovar la sesión."""

    # Crear un refresh y obtener su access token.
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)    
    
    access = str(refresh.access_token)

    # Intentar renovar utilizando el access token.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": access},
        format="json",
    )

    # El endpoint debe rechazar el tipo de token incorrecto.
    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"

    # No deben generarse nuevos tokens.
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rechaza_solicitud_sin_refresh(api_client, llaves):
    """La renovación requiere el campo refresh."""

    respuesta = api_client.post(
        URL_RENOVAR,
        {},
        format="json",
    )

    # Debe devolver un error de validación.
    assert respuesta.status_code == 400

    cuerpo = respuesta.json()

    # No deben entregarse tokens.
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo



def test_rechaza_refresh_revocado(api_client, usuario, llaves):
    """Un refresh válido pero revocado no debe renovar la sesión."""

    # Generar un refresh con los claims personalizados del proyecto.
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)

    # Comprobar que inicialmente es válido.
    refresh.check_blacklist()

    # Revocarlo explícitamente.
    refresh.blacklist()

    # Intentar renovar con el token revocado.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo

def test_access_renovado_dura_quince_minutos(api_client, usuario, llaves):
    """El access emitido durante la renovación debe durar 15 minutos."""

    # Crear un refresh válido.
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)

    # Solicitar la renovación.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data

    # Validar el access generado.
    access = AccessToken(respuesta.data["access"])

    duracion = access["exp"] - access["iat"]

    # Se admite un segundo de diferencia por el redondeo temporal.
    assert abs(duracion - 15 * 60) <= 1


def test_renovaciones_consecutivas_invalidan_refresh_anteriores(
    api_client, usuario, llaves
):
    """Cada renovación debe invalidar el refresh utilizado."""

    refresh_inicial = CustomTokenObtainPairSerializer.get_token(usuario)
    refresh_actual = str(refresh_inicial)

    tokens_utilizados = []

    # Realizar tres renovaciones consecutivas.
    for _ in range(3):
        respuesta = api_client.post(
            URL_RENOVAR,
            {"refresh": refresh_actual},
            format="json",
        )

        assert respuesta.status_code == 200, respuesta.data

        nuevo_refresh = respuesta.data["refresh"]

        # El nuevo refresh debe ser diferente del anterior.
        assert nuevo_refresh != refresh_actual

        tokens_utilizados.append(refresh_actual)
        refresh_actual = nuevo_refresh

    # Todos los refresh anteriores deben estar invalidados.
    for refresh_anterior in tokens_utilizados:
        respuesta = api_client.post(
            URL_RENOVAR,
            {"refresh": refresh_anterior},
            format="json",
        )

        assert respuesta.status_code == 401
        assert respuesta.json()["codigo"] == "token_invalido"

    # El último refresh generado debe seguir siendo válido.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_actual},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
