import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from usuarios.codigos import crear_codigo
from usuarios.models import Canal, Estado, Proposito
from usuarios.tests.factories import UsuarioFactory

URL = "/api/v1/auth/activar/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def pendiente():
    return UsuarioFactory(estado=Estado.PENDIENTE, email_verificado=False, telefono="+524431234567")


def _activar(cliente, identificador, codigo):
    return cliente.post(URL, {"identificador": identificador, "codigo": codigo}, format="json")


def _otro(plano):
    return "111111" if plano != "111111" else "222222"


def test_activa_por_correo(cliente, pendiente):
    _, plano = crear_codigo(pendiente, Proposito.ACTIVACION, Canal.CORREO)
    resp = _activar(cliente, pendiente.email, plano)
    assert resp.status_code == 200
    pendiente.refresh_from_db()
    assert pendiente.estado == Estado.ACTIVO
    assert pendiente.email_verificado is True


def test_activa_por_whatsapp(cliente, pendiente):
    _, plano = crear_codigo(pendiente, Proposito.ACTIVACION, Canal.WHATSAPP)
    resp = _activar(cliente, "443 123 4567", plano)
    assert resp.status_code == 200
    pendiente.refresh_from_db()
    assert pendiente.estado == Estado.ACTIVO
    assert pendiente.telefono_verificado is True


def test_codigo_incorrecto(cliente, pendiente):
    _, plano = crear_codigo(pendiente, Proposito.ACTIVACION)
    resp = _activar(cliente, pendiente.email, _otro(plano))
    assert resp.status_code == 400
    assert resp.json()["codigo"] == "codigo_invalido"


def test_codigo_vencido(cliente, pendiente):
    with freeze_time("2026-01-01 10:00:00"):
        _, plano = crear_codigo(pendiente, Proposito.ACTIVACION)
    with freeze_time("2026-01-01 10:11:00"):
        resp = _activar(cliente, pendiente.email, plano)
    assert resp.status_code == 400
    assert resp.json()["codigo"] == "codigo_expirado"


def test_codigo_usado_dos_veces(cliente, pendiente):
    _, plano = crear_codigo(pendiente, Proposito.ACTIVACION)
    assert _activar(cliente, pendiente.email, plano).status_code == 200
    resp = _activar(cliente, pendiente.email, plano)
    assert resp.status_code == 400
    assert resp.json()["codigo"] == "codigo_expirado"


def test_cinco_intentos_anulan_el_codigo(cliente, pendiente):
    _, plano = crear_codigo(pendiente, Proposito.ACTIVACION)
    for _ in range(5):
        resp = _activar(cliente, pendiente.email, _otro(plano))
        assert resp.json()["codigo"] == "codigo_invalido"
    resp = _activar(cliente, pendiente.email, plano)  # ya ni el correcto sirve
    assert resp.json()["codigo"] == "codigo_expirado"
    pendiente.refresh_from_db()
    assert pendiente.estado == Estado.PENDIENTE


def test_usuario_inexistente_no_se_revela(cliente):
    resp = _activar(cliente, "nadie@ejemplo.com", "123456")
    assert resp.status_code == 400
    assert resp.json()["codigo"] == "codigo_invalido"


def test_formato_de_codigo_invalido(cliente, pendiente):
    resp = _activar(cliente, pendiente.email, "12")
    assert resp.status_code == 400
    assert resp.json()["codigo"] == "datos_invalidos"