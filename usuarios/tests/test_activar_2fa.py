"""HU-30 / t-30/st-208: códigos de respaldo al confirmar el 2FA.

Complementa usuarios/tests/test_2fa_endpoints.py (st-206), que ya cubre la activación,
el secreto cifrado y el código incorrecto. Requiere st-207 (CodigoRespaldo).
"""
import pyotp
import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from usuarios.models import CodigoRespaldo
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

ACTIVAR = "/api/v1/auth/2fa/activar/"
CONFIRMAR = "/api/v1/auth/2fa/confirmar/"


@pytest.fixture(autouse=True)
def clave_de_cifrado(settings):
    settings.CLAVE_CIFRADO_2FA = Fernet.generate_key().decode()


@pytest.fixture
def sesion():
    usuario = UsuarioFactory()
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente, usuario


def codigo_incorrecto(secreto):
    totp = pyotp.TOTP(secreto)
    return next(c for c in ("000000", "111111", "222222") if not totp.verify(c, valid_window=1))


def activar_y_confirmar(cliente):
    secreto = cliente.post(ACTIVAR).json()["secreto"]
    return cliente.post(CONFIRMAR, {"codigo": pyotp.TOTP(secreto).now()}, format="json")


def test_confirmar_entrega_10_codigos_de_respaldo(sesion):
    cliente, _ = sesion
    r = activar_y_confirmar(cliente)

    assert r.status_code == 200
    codigos = r.json()["codigos_respaldo"]
    assert len(codigos) == 10
    assert len(set(codigos)) == 10


def test_los_codigos_se_guardan_con_hash(sesion):
    cliente, usuario = sesion
    codigos = activar_y_confirmar(cliente).json()["codigos_respaldo"]

    guardados = list(CodigoRespaldo.objects.filter(usuario=usuario))
    assert len(guardados) == 10
    for registro in guardados:
        assert all(c.replace("-", "") not in registro.codigo_hash for c in codigos)


def test_codigo_incorrecto_no_genera_codigos(sesion):
    cliente, usuario = sesion
    secreto = cliente.post(ACTIVAR).json()["secreto"]

    r = cliente.post(CONFIRMAR, {"codigo": codigo_incorrecto(secreto)}, format="json")

    assert r.status_code == 400
    assert r.json()["codigo"] == "codigo_invalido"
    assert not CodigoRespaldo.objects.filter(usuario=usuario).exists()


def test_los_codigos_no_vuelven_a_mostrarse(sesion):
    cliente, _ = sesion
    codigos = activar_y_confirmar(cliente).json()["codigos_respaldo"]

    otra = cliente.post(ACTIVAR)  # con el 2FA ya activo responde dos_factores_ya_activo

    assert otra.status_code == 400
    assert otra.json()["codigo"] == "dos_factores_ya_activo"
    assert all(c not in otra.content.decode() for c in codigos)


def test_los_codigos_no_van_a_la_bitacora(sesion, caplog):
    cliente, _ = sesion
    with caplog.at_level("INFO", logger="svc.auditoria"):
        codigos = activar_y_confirmar(cliente).json()["codigos_respaldo"]

    assert "2fa_activado" in caplog.text
    assert all(c not in caplog.text for c in codigos)