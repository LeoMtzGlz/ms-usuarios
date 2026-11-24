"""Pruebas de t-32/st-215 (HU-32): endpoint para desactivar el 2FA.

Pide contraseña y código; un administrador no puede desactivarlo; avisa por correo.
"""
import time

import pyotp
import pytest
from cryptography.fernet import Fernet
from rest_framework.test import APIClient

from comun.roles import Rol
from notificaciones.models import Notificacion
from notificaciones.worker import armar_mensaje
from usuarios.dos_factores import generar_codigos_respaldo
from usuarios.models import CodigoRespaldo, Dispositivo2FA
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory
from usuarios.views_2fa_desactivar import PASO_TOTP, intervalo_del_codigo

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/2fa/desactivar/"
ACTIVAR = "/api/v1/auth/2fa/activar/"


@pytest.fixture(autouse=True)
def clave_de_cifrado(settings):
    settings.CLAVE_CIFRADO_2FA = Fernet.generate_key().decode()


def _con_2fa(rol=Rol.CLIENTE, confirmado=True):
    usuario = UsuarioFactory(rol=rol)
    dispositivo = Dispositivo2FA(usuario=usuario)
    secreto = dispositivo.generar_secreto()
    dispositivo.confirmado = confirmado
    dispositivo.save()
    generar_codigos_respaldo(usuario)
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente, usuario, secreto


def _codigo(secreto):
    return pyotp.TOTP(secreto).now()


def _codigo_incorrecto(secreto):
    totp = pyotp.TOTP(secreto)
    return next(c for c in ("000000", "111111", "222222") if not totp.verify(c, valid_window=1))


def _desactivar(cliente, password, codigo):
    return cliente.post(URL, {"password": password, "codigo": codigo}, format="json")


# --- Caso correcto -------------------------------------------------------------

def test_cliente_desactiva_con_password_y_codigo():
    cliente, usuario, secreto = _con_2fa()
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"desactivado": True, "mensaje": "Verificación en dos pasos desactivada."}
    assert not Dispositivo2FA.objects.filter(usuario=usuario).exists()


def test_borra_los_codigos_de_respaldo():
    cliente, usuario, secreto = _con_2fa()
    assert CodigoRespaldo.objects.filter(usuario=usuario).count() == 10
    _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert not CodigoRespaldo.objects.filter(usuario=usuario).exists()


def test_operativo_tambien_puede_desactivar():
    cliente, usuario, secreto = _con_2fa(rol=Rol.OPERATIVO)
    assert _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto)).status_code == 200


def test_avisa_por_correo():
    cliente, usuario, secreto = _con_2fa()
    _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    aviso = Notificacion.objects.get(destinatario=usuario)
    assert aviso.canal == "correo"
    assert aviso.plantilla == "2fa_desactivado"
    assert aviso.estado == Notificacion.ESTADO_PENDIENTE


def test_el_aviso_se_puede_armar_y_no_lleva_datos_secretos():
    cliente, usuario, secreto = _con_2fa()
    codigo = _codigo(secreto)
    _desactivar(cliente, PASSWORD_PRUEBA, codigo)
    aviso = Notificacion.objects.get(destinatario=usuario)
    asunto, texto = armar_mensaje(aviso)  # la plantilla .txt que usa el worker
    assert asunto == "Se desactivó la verificación en dos pasos"
    assert "Hola Ana" in texto
    assert "se desactivó" in texto
    contenido = f"{aviso.contexto} {texto}"
    assert PASSWORD_PRUEBA not in contenido
    assert codigo not in contenido
    assert secreto not in contenido


def test_despues_puede_volver_a_activarlo():
    cliente, usuario, secreto = _con_2fa()
    _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert cliente.post(ACTIVAR).status_code == 200


def test_registra_el_evento_sin_password_ni_codigo(caplog):
    cliente, usuario, secreto = _con_2fa()
    codigo = _codigo(secreto)
    _desactivar(cliente, PASSWORD_PRUEBA, codigo)
    assert '"accion": "2fa_desactivado"' in caplog.text
    assert PASSWORD_PRUEBA not in caplog.text
    assert codigo not in caplog.text


# --- Administrador (HU-32: no puede desactivar su 2FA) --------------------------

def test_administrador_no_puede_desactivar():
    cliente, usuario, secreto = _con_2fa(rol=Rol.ADMINISTRADOR)
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "admin_requiere_2fa"
    assert Dispositivo2FA.objects.filter(usuario=usuario, confirmado=True).exists()
    assert not Notificacion.objects.filter(destinatario=usuario).exists()


# --- Errores: nada cambia --------------------------------------------------------

def _sigue_activo(usuario):
    return (
        Dispositivo2FA.objects.filter(usuario=usuario, confirmado=True).exists()
        and CodigoRespaldo.objects.filter(usuario=usuario).count() == 10
        and not Notificacion.objects.filter(destinatario=usuario).exists()
    )


def test_sin_sesion_responde_401():
    assert APIClient().post(URL, {"password": "x", "codigo": "123456"}, format="json").status_code == 401


def test_password_incorrecta():
    cliente, usuario, secreto = _con_2fa()
    respuesta = _desactivar(cliente, "NoEsLaMia123", _codigo(secreto))
    assert respuesta.status_code == 400
    assert respuesta.json()["campos"] == {"password": ["La contraseña es incorrecta."]}
    assert _sigue_activo(usuario)


def test_codigo_incorrecto():
    cliente, usuario, secreto = _con_2fa()
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, _codigo_incorrecto(secreto))
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "codigo_invalido"
    assert _sigue_activo(usuario)


def test_codigo_ya_usado_no_sirve():
    cliente, usuario, secreto = _con_2fa()
    Dispositivo2FA.objects.filter(usuario=usuario).update(ultimo_intervalo=int(time.time() // PASO_TOTP))
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "codigo_invalido"
    assert _sigue_activo(usuario)


@pytest.mark.parametrize("codigo", ["12345", "abcdef", "1234567", ""])
def test_formato_de_codigo_invalido(codigo):
    cliente, usuario, _ = _con_2fa()
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, codigo)
    assert respuesta.status_code == 400
    assert "codigo" in respuesta.json()["campos"]
    assert _sigue_activo(usuario)


def test_faltan_datos():
    cliente, usuario, _ = _con_2fa()
    respuesta = cliente.post(URL, {}, format="json")
    assert respuesta.status_code == 400
    assert set(respuesta.json()["campos"]) == {"password", "codigo"}


def test_sin_2fa_activo():
    usuario = UsuarioFactory()
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, "123456")
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "dos_factores_no_activo"


def test_2fa_iniciado_pero_sin_confirmar():
    cliente, usuario, secreto = _con_2fa(confirmado=False)
    respuesta = _desactivar(cliente, PASSWORD_PRUEBA, _codigo(secreto))
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "dos_factores_no_activo"


# --- intervalo_del_codigo ---------------------------------------------------------

def test_intervalo_acepta_el_anterior_y_rechaza_uno_viejo():
    secreto = pyotp.random_base32()
    totp = pyotp.TOTP(secreto)
    ahora = 1_800_000_000
    actual = ahora // PASO_TOTP
    assert intervalo_del_codigo(secreto, totp.at(ahora), ahora) == actual
    assert intervalo_del_codigo(secreto, totp.at(ahora - PASO_TOTP), ahora) == actual - 1
    viejo = totp.at(ahora - 5 * PASO_TOTP)
    if viejo not in {totp.at(ahora + d * PASO_TOTP) for d in (-1, 0, 1)}:
        assert intervalo_del_codigo(secreto, viejo, ahora) is None