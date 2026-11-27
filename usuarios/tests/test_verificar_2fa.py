"""t-31/st-211: POST /api/v1/auth/2fa/verificar/ (HU-31, criterios 2 y 3)."""

import json
import time

import pyotp
import pytest
from cryptography.fernet import Fernet
from django.core import signing
from rest_framework_simplejwt.tokens import RefreshToken

from comun.cifrado import cifrar
from usuarios.dos_factores import generar_codigos_respaldo
from usuarios.models import Dispositivo2FA, RegistroAcceso
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"
VERIFICAR = "/api/v1/auth/2fa/verificar/"
UN_DIA = 24 * 60 * 60
SIETE_DIAS = 7 * UN_DIA


@pytest.fixture(autouse=True)
def clave_de_cifrado(settings):
    settings.CLAVE_CIFRADO_2FA = Fernet.generate_key().decode()


@pytest.fixture
def secreto():
    return pyotp.random_base32()


@pytest.fixture
def usuario(llaves, secreto):
    usuario = UsuarioFactory()
    Dispositivo2FA.objects.create(usuario=usuario, secreto_cifrado=cifrar(secreto), confirmado=True)
    return usuario


def token_temporal(api_client, usuario, recordarme=False):
    datos = {"email": usuario.email, "password": PASSWORD_PRUEBA, "recordarme": recordarme}
    return api_client.post(LOGIN, datos, format="json").data["token_temporal"]


def otro_token_temporal(api_client, usuario, monkeypatch):
    """Un segundo login un segundo después; en el mismo segundo el token sería idéntico al primero."""
    despues = signing.b62_encode(int(time.time()) + 1)
    with monkeypatch.context() as m:
        m.setattr(signing.TimestampSigner, "timestamp", lambda self: despues)
        return token_temporal(api_client, usuario)


def verificar(api_client, token, codigo):
    return api_client.post(VERIFICAR, {"token_temporal": token, "codigo": codigo}, format="json")


def codigo_actual(secreto):
    return pyotp.TOTP(secreto).now()


def codigo_incorrecto(secreto):
    totp = pyotp.TOTP(secreto)
    return next(c for c in ("000000", "111111", "222222") if not totp.verify(c, valid_window=1))


# --- Código correcto ---


def test_el_codigo_de_la_app_entrega_los_jwt(api_client, usuario, secreto):
    r = verificar(api_client, token_temporal(api_client, usuario), codigo_actual(secreto))

    assert r.status_code == 200
    assert r.data["access"]
    assert r.data["refresh"]
    assert r.data["usuario"]["id"] == str(usuario.pk)


def test_registra_el_acceso_y_el_ultimo_login(api_client, usuario, secreto):
    verificar(api_client, token_temporal(api_client, usuario), codigo_actual(secreto))

    usuario.refresh_from_db()
    assert usuario.last_login is not None
    assert RegistroAcceso.objects.filter(usuario=usuario, exitoso=True).count() == 1


@pytest.mark.parametrize(("recordarme", "duracion"), [(True, SIETE_DIAS), (False, UN_DIA)])
def test_el_refresh_respeta_recordarme(api_client, usuario, secreto, recordarme, duracion):
    token = token_temporal(api_client, usuario, recordarme=recordarme)

    refresh = RefreshToken(verificar(api_client, token, codigo_actual(secreto)).data["refresh"])

    assert refresh["exp"] - refresh["iat"] == duracion
    assert refresh["recordarme"] is recordarme


def test_un_codigo_de_respaldo_entrega_los_jwt(api_client, usuario):
    codigo = generar_codigos_respaldo(usuario)[0]

    r = verificar(api_client, token_temporal(api_client, usuario), codigo)

    assert r.status_code == 200
    assert r.data["access"]


# --- Código incorrecto o repetido ---


def test_un_codigo_incorrecto_no_entrega_tokens(api_client, usuario, secreto):
    r = verificar(api_client, token_temporal(api_client, usuario), codigo_incorrecto(secreto))

    assert r.status_code == 400
    assert r.data["codigo"] == "codigo_invalido"
    assert "access" not in r.data
    usuario.refresh_from_db()
    assert usuario.last_login is None
    assert RegistroAcceso.objects.filter(usuario=usuario, exitoso=False).count() == 1


def test_el_mismo_codigo_de_la_app_no_sirve_dos_veces(api_client, usuario, secreto, monkeypatch):
    codigo = codigo_actual(secreto)
    assert verificar(api_client, token_temporal(api_client, usuario), codigo).status_code == 200

    r = verificar(api_client, otro_token_temporal(api_client, usuario, monkeypatch), codigo)

    assert r.status_code == 400
    assert r.data["codigo"] == "codigo_invalido"


def test_el_codigo_usado_al_confirmar_el_2fa_no_sirve(api_client, usuario, secreto):
    intervalo = int(time.time() // 30)
    Dispositivo2FA.objects.filter(usuario=usuario).update(ultimo_intervalo=intervalo)

    r = verificar(api_client, token_temporal(api_client, usuario), pyotp.TOTP(secreto).at(intervalo * 30))

    assert r.status_code == 400


def test_el_codigo_de_respaldo_solo_sirve_una_vez(api_client, usuario, monkeypatch):
    codigo = generar_codigos_respaldo(usuario)[0]
    assert verificar(api_client, token_temporal(api_client, usuario), codigo).status_code == 200

    r = verificar(api_client, otro_token_temporal(api_client, usuario, monkeypatch), codigo)

    assert r.status_code == 400
    assert r.data["codigo"] == "codigo_invalido"


# --- Máximo 5 intentos ---


def test_el_quinto_intento_todavia_se_evalua(api_client, usuario, secreto):
    token = token_temporal(api_client, usuario)
    for _ in range(4):
        verificar(api_client, token, codigo_incorrecto(secreto))

    assert verificar(api_client, token, codigo_actual(secreto)).status_code == 200


def test_despues_de_5_intentos_se_bloquea_aunque_el_codigo_sea_correcto(api_client, usuario, secreto):
    token = token_temporal(api_client, usuario)
    for _ in range(5):
        assert verificar(api_client, token, codigo_incorrecto(secreto)).status_code == 400

    r = verificar(api_client, token, codigo_actual(secreto))

    assert r.status_code == 429
    assert r.data["codigo"] == "demasiados_intentos"
    assert "access" not in r.data


def test_un_login_nuevo_no_reinicia_los_intentos(api_client, usuario, secreto):
    token = token_temporal(api_client, usuario)
    for _ in range(5):
        verificar(api_client, token, codigo_incorrecto(secreto))

    r = verificar(api_client, token_temporal(api_client, usuario), codigo_actual(secreto))

    assert r.status_code == 429


# --- Token temporal ---


def test_el_token_temporal_es_de_un_solo_uso(api_client, usuario, secreto):
    codigos = generar_codigos_respaldo(usuario)
    token = token_temporal(api_client, usuario)
    assert verificar(api_client, token, codigos[0]).status_code == 200

    r = verificar(api_client, token, codigos[1])

    assert r.status_code == 401
    assert r.data["codigo"] == "token_invalido"


def test_un_token_temporal_invalido_responde_401(api_client, usuario, secreto):
    r = verificar(api_client, "no-es-un-token", codigo_actual(secreto))

    assert r.status_code == 401
    assert r.data["codigo"] == "token_invalido"


def test_si_desactiva_su_2fa_el_token_ya_no_sirve(api_client, usuario, secreto):
    token = token_temporal(api_client, usuario)
    Dispositivo2FA.objects.filter(usuario=usuario).update(confirmado=False)

    r = verificar(api_client, token, codigo_actual(secreto))

    assert r.status_code == 401


def test_faltan_datos_responde_400(api_client):
    r = api_client.post(VERIFICAR, {}, format="json")

    assert r.status_code == 400
    assert set(r.data["campos"]) == {"token_temporal", "codigo"}


# --- Bitácora ---


def test_la_bitacora_no_guarda_el_codigo_ni_el_token(api_client, usuario, secreto, caplog):
    token = token_temporal(api_client, usuario)
    incorrecto = codigo_incorrecto(secreto)
    correcto = codigo_actual(secreto)
    caplog.clear()

    verificar(api_client, token, incorrecto)
    verificar(api_client, token, correcto)

    eventos = [json.loads(r.message) for r in caplog.records if r.name == "svc.auditoria"]
    assert [e["accion"] for e in eventos] == ["login_2fa_fallido", "login_2fa_completado"]
    texto = " ".join(r.message for r in caplog.records)
    assert token not in texto
    assert incorrecto not in texto
    assert correcto not in texto
