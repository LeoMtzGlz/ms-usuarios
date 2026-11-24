"""Pruebas de HU-06/ST-87: duración del refresh del login con y sin "recordarme" (ST-85).

Hacen peticiones reales a POST /api/v1/auth/login/ y firman con las llaves temporales
del fixture `llaves` de conftest.py. Las duraciones aceptan ±1 segundo para no ser inestables.
"""
from datetime import timedelta

import pytest
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch

from .factories import PASSWORD_PRUEBA

pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
UN_DIA = timedelta(days=1).total_seconds()
SIETE_DIAS = timedelta(days=7).total_seconds()
QUINCE_MINUTOS = timedelta(minutes=15).total_seconds()


def _login(api_client, usuario, **extra):
    """Inicia sesión con la contraseña conocida del usuario y los campos extra que se pasen."""
    return api_client.post(
        URL_LOGIN, {"email": usuario.email, "password": PASSWORD_PRUEBA, **extra}, format="json"
    )


def _duracion(token):
    """Segundos entre la emisión (iat) y el vencimiento (exp) de un token."""
    return token["exp"] - token["iat"]


def _dura(token, segundos):
    return abs(_duracion(token) - segundos) <= 1


def test_sin_recordarme_el_refresh_dura_un_dia(api_client, usuario, llaves):
    respuesta = _login(api_client, usuario)

    assert respuesta.status_code == 200
    refresh = RefreshToken(respuesta.data["refresh"])
    assert _dura(refresh, UN_DIA)
    assert refresh["recordarme"] is False


def test_recordarme_false_explicito_dura_un_dia(api_client, usuario, llaves):
    respuesta = _login(api_client, usuario, recordarme=False)

    assert respuesta.status_code == 200
    refresh = RefreshToken(respuesta.data["refresh"])
    assert _dura(refresh, UN_DIA)
    assert refresh["recordarme"] is False


def test_con_recordarme_el_refresh_dura_siete_dias(api_client, usuario, llaves):
    respuesta = _login(api_client, usuario, recordarme=True)

    assert respuesta.status_code == 200
    refresh = RefreshToken(respuesta.data["refresh"])
    assert _dura(refresh, SIETE_DIAS)
    assert refresh["recordarme"] is True


@pytest.mark.parametrize("extra", [{}, {"recordarme": False}, {"recordarme": True}])
def test_el_access_dura_quince_minutos_en_todos_los_casos(api_client, usuario, llaves, extra):
    respuesta = _login(api_client, usuario, **extra)

    assert respuesta.status_code == 200
    assert _dura(AccessToken(respuesta.data["access"]), QUINCE_MINUTOS)


@pytest.mark.parametrize("recordarme", [False, True])
def test_outstanding_token_vence_igual_que_el_refresh(api_client, usuario, llaves, recordarme):
    respuesta = _login(api_client, usuario, recordarme=recordarme)

    refresh = RefreshToken(respuesta.data["refresh"])
    registro = OutstandingToken.objects.get(jti=refresh["jti"])
    diferencia = registro.expires_at - datetime_from_epoch(refresh["exp"])
    assert abs(diferencia.total_seconds()) <= 1


def test_recordarme_no_booleano_responde_400_sin_tokens(api_client, usuario, llaves):
    respuesta = _login(api_client, usuario, recordarme="quizas")

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "datos_invalidos"
    assert "recordarme" in cuerpo["campos"]
    assert "access" not in cuerpo and "refresh" not in cuerpo


def test_credenciales_invalidas_con_recordarme_siguen_fallando(api_client, usuario, llaves):
    respuesta = api_client.post(
        URL_LOGIN, {"email": usuario.email, "password": "Incorrecta123", "recordarme": True}, format="json"
    )

    assert respuesta.status_code == 401
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "credenciales_invalidas"
    assert "access" not in cuerpo and "refresh" not in cuerpo
