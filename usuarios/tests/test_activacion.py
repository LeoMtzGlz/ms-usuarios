"""HU-03 / ST-73: Pruebas de activación."""

import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from usuarios.codigos import crear_codigo
from usuarios.models import Canal, Estado, Proposito
from usuarios.tests.factories import UsuarioFactory

URL = "/api/v1/auth/activar/"

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def usuario_pendiente():
    return UsuarioFactory(estado=Estado.PENDIENTE, email_verificado=False)

def _activar(api_client, identificador, codigo):
    return api_client.post(
        URL,
        {"identificador": identificador, "codigo": codigo},
        format="json",
    )

@pytest.mark.django_db
def test_correcto_por_correo(api_client, usuario_pendiente):
    """ST-73: Código correcto por correo activa."""
    _, codigo = crear_codigo(usuario_pendiente, Proposito.ACTIVACION, canal=Canal.CORREO)

    respuesta = _activar(api_client, usuario_pendiente.email, codigo)

    assert respuesta.status_code == 200, respuesta.data
    usuario_pendiente.refresh_from_db()
    assert usuario_pendiente.estado == Estado.ACTIVO
    assert usuario_pendiente.email_verificado is True

@pytest.mark.django_db
def test_correcto_por_whatsapp(api_client):
    """ST-73: Código correcto por WhatsApp activa y marca telefono."""
    usuario = UsuarioFactory(
        estado=Estado.PENDIENTE,
        telefono_verificado=False,
        canal_preferido=Canal.WHATSAPP,
    )
    _, codigo = crear_codigo(usuario, Proposito.ACTIVACION, canal=Canal.WHATSAPP)

    respuesta = _activar(api_client, usuario.email, codigo)

    assert respuesta.status_code == 200, respuesta.data
    usuario.refresh_from_db()
    assert usuario.estado == Estado.ACTIVO
    assert usuario.telefono_verificado is True

@pytest.mark.django_db
def test_incorrecto_no_activa(api_client, usuario_pendiente):
    """ST-73: Código incorrecto no activa."""
    crear_codigo(usuario_pendiente, Proposito.ACTIVACION)

    respuesta = _activar(api_client, usuario_pendiente.email, "000000")

    assert respuesta.status_code == 400
    usuario_pendiente.refresh_from_db()
    assert usuario_pendiente.estado == Estado.PENDIENTE

@pytest.mark.django_db
def test_vencido_no_activa(api_client, usuario_pendiente):
    """ST-73: Código vencido no activa."""
    registro, codigo = crear_codigo(usuario_pendiente, Proposito.ACTIVACION)
    # Lo vencemos a mano: expira_en en el pasado
    registro.expira_en = timezone.now() - timedelta(minutes=1)
    registro.save(update_fields=["expira_en"])

    respuesta = _activar(api_client, usuario_pendiente.email, codigo)

    assert respuesta.status_code == 400
    usuario_pendiente.refresh_from_db()
    assert usuario_pendiente.estado == Estado.PENDIENTE

@pytest.mark.django_db
def test_usado_dos_veces_solo_primera_pasa(api_client, usuario_pendiente):
    """ST-73: Código de un solo uso, la segunda vez falla."""
    _, codigo = crear_codigo(usuario_pendiente, Proposito.ACTIVACION)

    primera = _activar(api_client, usuario_pendiente.email, codigo)
    assert primera.status_code == 200

    segunda = _activar(api_client, usuario_pendiente.email, codigo)
    assert segunda.status_code == 400

@pytest.mark.django_db
def test_cinco_intentos_bloquea(api_client, usuario_pendiente):
    """ST-73: 5 intentos fallidos bloquean el código."""
    crear_codigo(usuario_pendiente, Proposito.ACTIVACION)

    for _ in range(5):
        respuesta = _activar(api_client, usuario_pendiente.email, "000000")
        assert respuesta.status_code == 400

    usuario_pendiente.refresh_from_db()
    assert usuario_pendiente.estado == Estado.PENDIENTE