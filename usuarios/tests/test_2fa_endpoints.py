#t-30/st-206
"""t-30 / st-206: endpoints para activar y confirmar el 2FA."""
import pyotp
import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from usuarios.models import Dispositivo2FA
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
    return next(
        c for c in ("000000", "111111", "222222")
        if not totp.verify(c, valid_window=1)
    )


def test_activar_exige_sesion():
    assert APIClient().post(ACTIVAR).status_code == 401


def test_activar_devuelve_secreto_uri_y_qr(sesion):
    cliente, _ = sesion
    r = cliente.post(ACTIVAR)

    assert r.status_code == 200
    assert r.json()["uri"].startswith("otpauth://totp/")
    assert r.json()["qr_base64"].startswith("iVBOR")  # firma de un PNG en base64


def test_el_secreto_se_guarda_cifrado_y_sin_confirmar(sesion):
    cliente, usuario = sesion
    secreto = cliente.post(ACTIVAR).json()["secreto"]
    dispositivo = Dispositivo2FA.objects.get(usuario=usuario)

    assert dispositivo.secreto_cifrado != secreto
    assert dispositivo.secreto == secreto
    assert dispositivo.confirmado is False


def test_activar_otra_vez_antes_de_confirmar_cambia_el_secreto(sesion):
    cliente, _ = sesion
    primero = cliente.post(ACTIVAR).json()["secreto"]
    segundo = cliente.post(ACTIVAR).json()["secreto"]

    assert primero != segundo


def test_confirmar_con_codigo_correcto_activa_el_2fa(sesion):
    cliente, usuario = sesion
    secreto = cliente.post(ACTIVAR).json()["secreto"]

    r = cliente.post(CONFIRMAR, {"codigo": pyotp.TOTP(secreto).now()}, format="json")

    assert r.status_code == 200
    assert Dispositivo2FA.objects.get(usuario=usuario).confirmado is True


def test_confirmar_con_codigo_incorrecto_no_activa(sesion):
    cliente, usuario = sesion
    secreto = cliente.post(ACTIVAR).json()["secreto"]

    r = cliente.post(CONFIRMAR, {"codigo": codigo_incorrecto(secreto)}, format="json")

    assert r.status_code == 400
    assert r.json()["codigo"] == "codigo_invalido"
    assert Dispositivo2FA.objects.get(usuario=usuario).confirmado is False


def test_confirmar_sin_haber_activado(sesion):
    cliente, _ = sesion
    r = cliente.post(CONFIRMAR, {"codigo": "123456"}, format="json")

    assert r.status_code == 400
    assert r.json()["codigo"] == "dos_factores_no_iniciado"


def test_confirmar_con_formato_invalido(sesion):
    cliente, _ = sesion
    cliente.post(ACTIVAR)
    r = cliente.post(CONFIRMAR, {"codigo": "abc"}, format="json")

    assert r.status_code == 400
    assert r.json()["codigo"] == "datos_invalidos"
    assert "codigo" in r.json()["campos"]


def test_no_se_puede_activar_si_ya_esta_confirmado(sesion):
    cliente, _ = sesion
    secreto = cliente.post(ACTIVAR).json()["secreto"]
    cliente.post(CONFIRMAR, {"codigo": pyotp.TOTP(secreto).now()}, format="json")

    r = cliente.post(ACTIVAR)

    assert r.status_code == 400
    assert r.json()["codigo"] == "dos_factores_ya_activo"