"""HU-26 / ST-190: cada flujo que llama a registrar_evento() deja su fila en la bitácora."""
import pyotp
import pytest
from cryptography.fernet import Fernet
from django.core.management import call_command

from comun.models import EventoAuditoria
from comun.roles import Rol
from usuarios.models import Estado, Usuario, Zona
from usuarios.tests.factories import UsuarioFactory
from usuarios.tests.helpers_admin import api_de

pytestmark = pytest.mark.django_db

AUDITORIA = "/api/v1/auditoria/"
REGISTRO = "/api/v1/auth/registro/"
ALTA = "/api/v1/usuarios/"
PRIVACIDAD = "/api/v1/auth/privacidad/aceptar/"
ACTIVAR_2FA = "/api/v1/auth/2fa/activar/"
CONFIRMAR_2FA = "/api/v1/auth/2fa/confirmar/"

PASSWORD_REGISTRO = "Registro2026"
PASSWORD_NUEVA = "Definitiva2026"
PASSWORD_ADMIN_CMD = "Segura123x"


@pytest.fixture(autouse=True)
def preparacion(settings, llaves):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.CLAVE_CIFRADO_2FA = Fernet.generate_key().decode()


# Cada flujo recibe (api_client, monkeypatch) y devuelve el usuario que debe quedar en el evento.

def flujo_registro(api_client, monkeypatch):
    datos = {
        "nombre": "María", "apellidos": "Hernández Ruiz", "correo": "maria.hernandez@ejemplo.com",
        "telefono": "443 123 4567", "password": PASSWORD_REGISTRO,
        "password_confirmacion": PASSWORD_REGISTRO, "canal_preferido": "whatsapp", "acepto_privacidad": True,
    }
    assert api_client.post(REGISTRO, datos, format="json").status_code == 201
    return Usuario.objects.get(email="maria.hernandez@ejemplo.com")


def flujo_alta_usuario(api_client, monkeypatch):
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR)
    zona, _ = Zona.objects.get_or_create(nombre="Centro", defaults={"activa": True})
    datos = {"nombre": "Luis", "apellidos": "Ramírez Soto", "correo": "luis.ramirez@ejemplo.com",
             "telefono": "443 123 4567", "zona": zona.pk}
    r = api_de(admin).post(ALTA, datos, format="json")
    assert r.status_code == 201
    return admin


def flujo_password_cambiado(api_client, monkeypatch):
    usuario = UsuarioFactory(debe_cambiar_password=True)
    usuario.cambiar_password(PASSWORD_NUEVA)
    return usuario


def flujo_estado_cambiado(api_client, monkeypatch):
    usuario = UsuarioFactory()
    usuario.cambiar_estado(Estado.INACTIVO)
    return usuario


def flujo_privacidad_aceptada(api_client, monkeypatch):
    usuario = UsuarioFactory()
    api_client.force_authenticate(user=usuario)
    assert api_client.post(PRIVACIDAD).status_code == 200
    return usuario


def flujo_2fa_activacion_iniciada(api_client, monkeypatch):
    usuario = UsuarioFactory()
    api_client.force_authenticate(user=usuario)
    assert api_client.post(ACTIVAR_2FA).status_code == 200
    return usuario


def flujo_2fa_activado(api_client, monkeypatch):
    usuario = UsuarioFactory()
    api_client.force_authenticate(user=usuario)
    secreto = api_client.post(ACTIVAR_2FA).json()["secreto"]
    assert api_client.post(CONFIRMAR_2FA, {"codigo": pyotp.TOTP(secreto).now()}, format="json").status_code == 200
    return usuario


def flujo_2fa_confirmacion_fallida(api_client, monkeypatch):
    usuario = UsuarioFactory()
    api_client.force_authenticate(user=usuario)
    secreto = api_client.post(ACTIVAR_2FA).json()["secreto"]
    totp = pyotp.TOTP(secreto)
    malo = next(c for c in ("000000", "111111", "222222") if not totp.verify(c, valid_window=1))
    assert api_client.post(CONFIRMAR_2FA, {"codigo": malo}, format="json").status_code == 400
    return usuario


def flujo_admin_creado(api_client, monkeypatch):
    respuestas = iter((PASSWORD_ADMIN_CMD, PASSWORD_ADMIN_CMD))
    monkeypatch.setattr("getpass.getpass", lambda *a, **k: next(respuestas))
    call_command("crear_admin", "Admin@Ejemplo.com", "--nombre", "Ana", "--apellidos", "López")
    return Usuario.objects.get(email="admin@ejemplo.com")


FLUJOS = [
    ("registro", flujo_registro),
    ("alta_usuario", flujo_alta_usuario),
    ("password_cambiado", flujo_password_cambiado),
    ("estado_cambiado", flujo_estado_cambiado),
    ("privacidad_aceptada", flujo_privacidad_aceptada),
    ("2fa_activacion_iniciada", flujo_2fa_activacion_iniciada),
    ("2fa_activado", flujo_2fa_activado),
    ("2fa_confirmacion_fallida", flujo_2fa_confirmacion_fallida),
    ("admin_creado", flujo_admin_creado),
]


@pytest.mark.parametrize("accion,flujo", FLUJOS, ids=[f[0] for f in FLUJOS])
def test_cada_flujo_crea_su_evento(api_client, monkeypatch, accion, flujo):
    usuario = flujo(api_client, monkeypatch)

    evento = EventoAuditoria.objects.get(accion=accion)
    assert evento.usuario == usuario
    if accion != "2fa_confirmacion_fallida":  # su resultado se prueba aparte (xfail)
        assert evento.resultado == "ok"


def test_2fa_confirmacion_fallida_se_registra_con_resultado_error(api_client, monkeypatch):
    flujo_2fa_confirmacion_fallida(api_client, monkeypatch)

    assert EventoAuditoria.objects.get(accion="2fa_confirmacion_fallida").resultado == "error"


def test_ningun_evento_guarda_la_contrasena(api_client, monkeypatch):
    flujo_registro(api_client, monkeypatch)
    flujo_password_cambiado(api_client, monkeypatch)
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR)
    zona, _ = Zona.objects.get_or_create(nombre="Centro", defaults={"activa": True})
    r = api_de(admin).post(
        ALTA,
        {"nombre": "Luis", "apellidos": "Ramírez Soto", "correo": "luis.ramirez@ejemplo.com",
         "telefono": "443 765 4321", "zona": zona.pk},
        format="json",
    )
    temporal = r.json()["contrasena_temporal"]

    assert EventoAuditoria.objects.count() >= 3
    for e in EventoAuditoria.objects.all():
        texto = f"{e.detalles} {e.user_agent}"
        for secreto in (PASSWORD_REGISTRO, PASSWORD_NUEVA, temporal):
            assert secreto not in texto


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_no_administrador_recibe_403_en_la_bitacora(api_client, rol):
    flujo_privacidad_aceptada(api_client, None)
    api_client.force_authenticate(user=None)

    r = api_de(UsuarioFactory(rol=rol)).get(AUDITORIA)
    assert r.status_code == 403
    assert r.json()["codigo"] == "sin_permiso"

    # El administrador del mismo escenario sí ve el evento.
    r = api_de(UsuarioFactory(rol=Rol.ADMINISTRADOR)).get(AUDITORIA, {"accion": "privacidad_aceptada"})
    assert r.status_code == 200
    assert [f["accion"] for f in r.json()["results"]] == ["privacidad_aceptada"]
