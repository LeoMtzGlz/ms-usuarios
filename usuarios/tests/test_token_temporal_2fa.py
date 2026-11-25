"""t-31/st-210: el login devuelve un token temporal cuando el usuario tiene 2FA (HU-31, criterio 1)."""

import time

import pytest
from django.core import signing

from comun.errores import TokenInvalido
from usuarios.login_2fa import SALT, VIGENCIA_SEGUNDOS, emitir_token_temporal, leer_token_temporal
from usuarios.models import Dispositivo2FA, Estado
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"


def con_2fa(usuario, confirmado=True):
    # En la st-210 no se descifra el secreto, así que basta con un valor cualquiera.
    Dispositivo2FA.objects.create(usuario=usuario, secreto_cifrado="no-se-usa", confirmado=confirmado)
    return usuario


def login(api_client, usuario, password=PASSWORD_PRUEBA):
    return api_client.post(LOGIN, {"email": usuario.email, "password": password}, format="json")


# --- Login ---


def test_sin_2fa_el_login_entrega_los_jwt(api_client, llaves):
    respuesta = login(api_client, UsuarioFactory())

    assert respuesta.status_code == 200
    assert "access" in respuesta.data and "refresh" in respuesta.data
    assert "token_temporal" not in respuesta.data


def test_con_2fa_el_login_entrega_token_temporal_y_no_los_jwt(api_client):
    respuesta = login(api_client, con_2fa(UsuarioFactory()))

    assert respuesta.status_code == 200
    assert respuesta.data["requiere_2fa"] is True
    assert respuesta.data["expira_en"] == VIGENCIA_SEGUNDOS
    assert respuesta.data["token_temporal"]
    assert "access" not in respuesta.data and "refresh" not in respuesta.data


def test_2fa_sin_confirmar_no_cambia_el_login(api_client, llaves):
    respuesta = login(api_client, con_2fa(UsuarioFactory(), confirmado=False))

    assert respuesta.status_code == 200
    assert "access" in respuesta.data
    assert "token_temporal" not in respuesta.data


def test_con_2fa_y_contrasena_incorrecta_no_hay_token_temporal(api_client):
    respuesta = login(api_client, con_2fa(UsuarioFactory()), password="Incorrecta123")

    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "credenciales_invalidas"
    assert "token_temporal" not in respuesta.data


def test_con_2fa_no_se_actualiza_last_login(api_client):
    usuario = con_2fa(UsuarioFactory(last_login=None))
    login(api_client, usuario)

    usuario.refresh_from_db()
    assert usuario.last_login is None


def test_registra_el_evento_sin_el_token(api_client, caplog):
    with caplog.at_level("INFO", logger="svc.auditoria"):
        token = login(api_client, con_2fa(UsuarioFactory())).data["token_temporal"]

    assert "login_requiere_2fa" in caplog.text
    assert token not in caplog.text


# --- Token temporal ---


def test_el_token_identifica_al_usuario():
    usuario = UsuarioFactory()
    assert leer_token_temporal(emitir_token_temporal(usuario)) == (usuario, False)


@pytest.mark.parametrize("recordarme", [True, False])
def test_el_token_conserva_la_opcion_recordarme_del_login(api_client, recordarme):
    """La st-211 necesita saber si el refresh dura 7 días o 1 (st-85)."""
    usuario = con_2fa(UsuarioFactory())
    datos = {"email": usuario.email, "password": PASSWORD_PRUEBA, "recordarme": recordarme}
    token = api_client.post(LOGIN, datos, format="json").data["token_temporal"]

    assert leer_token_temporal(token) == (usuario, recordarme)


def test_el_token_vence_a_los_5_minutos(monkeypatch):
    token = emitir_token_temporal(UsuarioFactory())
    ahora = time.time()
    monkeypatch.setattr(signing.time, "time", lambda: ahora + VIGENCIA_SEGUNDOS + 1)

    with pytest.raises(TokenInvalido):
        leer_token_temporal(token)


def test_el_token_alterado_se_rechaza():
    token = emitir_token_temporal(UsuarioFactory())
    with pytest.raises(TokenInvalido):
        leer_token_temporal(token[:-2] + "xx")


def test_un_token_firmado_con_otro_salt_se_rechaza():
    usuario = UsuarioFactory()
    ajeno = signing.TimestampSigner(salt="otro").sign_object({"uid": str(usuario.pk), "tv": usuario.token_version})

    assert SALT != "otro"
    with pytest.raises(TokenInvalido):
        leer_token_temporal(ajeno)


def test_el_token_deja_de_servir_si_cambia_token_version():
    """Cerrar todas las sesiones o cambiar la contraseña incrementa token_version."""
    usuario = UsuarioFactory()
    token = emitir_token_temporal(usuario)
    usuario.token_version += 1
    usuario.save(update_fields=["token_version"])

    with pytest.raises(TokenInvalido):
        leer_token_temporal(token)


def test_el_token_no_sirve_si_la_cuenta_ya_no_esta_activa():
    usuario = UsuarioFactory()
    token = emitir_token_temporal(usuario)
    usuario.estado = Estado.INACTIVO
    usuario.save(update_fields=["estado"])

    with pytest.raises(TokenInvalido):
        leer_token_temporal(token)
