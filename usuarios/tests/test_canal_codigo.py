"""HU-01 / ST-61: el registro avisa por qué canal sale el código."""
from unittest import mock

import pytest

from notificaciones.models import Notificacion
from usuarios.codigos import generar_codigo
from usuarios.models import Proposito, Usuario
from usuarios.tests.factories import UsuarioFactory
from usuarios.tests.test_registro_endpoint import URL, datos_validos

pytestmark = pytest.mark.django_db


def test_registro_con_whatsapp_dice_whatsapp(api_client):
    respuesta = api_client.post(URL, datos_validos(canal_preferido="whatsapp"), format="json")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["canal_codigo"] == "whatsapp"
    assert cuerpo["canal_sustituido"] is False
    assert Notificacion.objects.get().canal == "whatsapp"


def test_registro_con_correo_dice_correo(api_client):
    respuesta = api_client.post(URL, datos_validos(canal_preferido="correo"), format="json")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["canal_codigo"] == "correo"
    assert cuerpo["canal_sustituido"] is False


def test_registro_avisa_cuando_el_codigo_sale_por_correo(api_client, monkeypatch):
    monkeypatch.setattr("usuarios.codigos.elegir_canal", lambda usuario, canal=None: "correo")

    respuesta = api_client.post(URL, datos_validos(canal_preferido="whatsapp"), format="json")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["canal_codigo"] == "correo"
    assert cuerpo["canal_sustituido"] is True


def test_whatsapp_sin_telefono_se_sustituye_por_correo():
    usuario = UsuarioFactory(telefono=None, canal_preferido="whatsapp")

    registro = generar_codigo(usuario, Proposito.ACTIVACION)

    assert registro.canal == "correo"
    assert registro.canal != usuario.canal_preferido


def test_la_respuesta_no_expone_el_codigo_ni_tokens(api_client):
    cuerpo = api_client.post(URL, datos_validos(), format="json").json()

    for clave in ("access", "refresh", "token", "password", "password_confirmacion", "codigo"):
        assert clave not in cuerpo
    for clave in ("id", "nombre", "apellidos", "correo", "telefono", "canal_preferido", "rol", "estado"):
        assert clave in cuerpo


def test_registro_fallido_no_cambia_su_error(api_client):
    api_client.raise_request_exception = False
    with mock.patch("usuarios.views.generar_codigo", side_effect=RuntimeError("boom")):
        respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 500
    assert Usuario.objects.count() == 0
