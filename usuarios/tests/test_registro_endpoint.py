"""HU-02 / ST-66: pruebas de POST /api/v1/auth/registro/."""
from unittest import mock

import pytest
from django.contrib.auth.hashers import check_password
from django.urls import reverse

from comun.roles import Rol
from notificaciones.models import Notificacion
from usuarios.models import CodigoVerificacion, Estado, Proposito, Usuario
from usuarios.serializers import CORREO_REGISTRADO
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/registro/"


def datos_validos(**cambios):
    datos = {
        "nombre": "María",
        "apellidos": "Hernández Ruiz",
        "correo": "maria.hernandez@ejemplo.com",
        "telefono": "443 123 4567",
        "password": "Registro2026",
        "password_confirmacion": "Registro2026",
        "canal_preferido": "whatsapp",
        "acepto_privacidad": True,
    }
    datos.update(cambios)
    return datos


def test_la_ruta_es_la_del_backlog():
    assert reverse("auth:registro") == URL


# Caso feliz

def test_registro_responde_201_sin_tokens_ni_contrasenas(api_client):
    respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["correo"] == "maria.hernandez@ejemplo.com"
    assert cuerpo["telefono"] == "+524431234567"
    assert cuerpo["estado"] == Estado.PENDIENTE
    assert cuerpo["rol"] == Rol.CLIENTE
    for clave in ("access", "refresh", "token", "password", "password_confirmacion"):
        assert clave not in cuerpo


def test_crea_la_cuenta_pendiente_de_cliente(api_client):
    api_client.post(URL, datos_validos(), format="json")

    usuario = Usuario.objects.get(email="maria.hernandez@ejemplo.com")
    assert usuario.estado == Estado.PENDIENTE
    assert usuario.rol == Rol.CLIENTE
    assert usuario.check_password("Registro2026")
    assert usuario.acepto_privacidad_en is not None


def test_crea_un_codigo_de_activacion_guardado_con_hash(api_client):
    api_client.post(URL, datos_validos(), format="json")

    usuario = Usuario.objects.get(email="maria.hernandez@ejemplo.com")
    codigo = CodigoVerificacion.objects.get(usuario=usuario)
    assert codigo.proposito == Proposito.ACTIVACION
    assert codigo.canal == "whatsapp"
    assert codigo.usado is False
    assert codigo.expira_en > codigo.creado_en
    assert len(codigo.codigo_hash) > 6  # no es el código en claro


def test_encola_la_notificacion_con_el_codigo(api_client):
    api_client.post(URL, datos_validos(), format="json")

    usuario = Usuario.objects.get(email="maria.hernandez@ejemplo.com")
    notificacion = Notificacion.objects.get(destinatario=usuario)
    assert notificacion.plantilla == "codigo_activacion"
    assert notificacion.canal == "whatsapp"  # el canal_preferido de la persona
    assert notificacion.estado == Notificacion.ESTADO_PENDIENTE

    # El código enviado es el que corresponde al hash guardado
    codigo_enviado = notificacion.contexto["codigo"]
    assert len(codigo_enviado) == 6 and codigo_enviado.isdigit()
    assert check_password(codigo_enviado, CodigoVerificacion.objects.get(usuario=usuario).codigo_hash)


def test_es_publico_aunque_llegue_un_token_invalido(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer token-que-no-sirve")
    respuesta = api_client.post(URL, datos_validos(), format="json")
    assert respuesta.status_code == 201


# Errores

def test_datos_invalidos_responden_400_con_el_formato_estandar(api_client):
    UsuarioFactory(email="maria.hernandez@ejemplo.com")
    respuesta = api_client.post(URL, datos_validos(correo="MARIA.Hernandez@ejemplo.com"), format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert respuesta.json()["campos"]["correo"] == [CORREO_REGISTRADO]


def test_si_hay_errores_no_crea_nada(api_client):
    respuesta = api_client.post(URL, datos_validos(acepto_privacidad=False), format="json")

    assert respuesta.status_code == 400
    assert not Usuario.objects.exists()
    assert not CodigoVerificacion.objects.exists()
    assert not Notificacion.objects.exists()


def test_solo_acepta_post(api_client):
    assert api_client.get(URL).status_code == 405


# Transacción

@pytest.mark.parametrize("falla_en", ["usuarios.codigos.notificar", "usuarios.codigos.crear_codigo"])
def test_si_falla_el_codigo_o_la_notificacion_no_queda_la_cuenta(api_client, falla_en):
    api_client.raise_request_exception = False
    with mock.patch(falla_en, side_effect=RuntimeError("falla simulada")):
        respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 500
    assert not Usuario.objects.exists()
    assert not CodigoVerificacion.objects.exists()
    assert not Notificacion.objects.exists()