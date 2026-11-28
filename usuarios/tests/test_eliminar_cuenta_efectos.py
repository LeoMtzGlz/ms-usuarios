"""HU-23 / ST-175: efectos de eliminar la cuenta, comprobados de punta a punta por la API.

test_eliminar_cuenta.py (ST-174) prueba el contrato del endpoint (validaciones, correo, administrador)
y test_anonimizacion.py (ST-173) prueba la función por separado. Aquí se comprueba, con el endpoint real,
que cada criterio de HU-23 se cumple: datos anonimizados, sesiones cerradas, registros conservados,
credenciales borradas y correo/teléfono libres.
"""
import json
from unittest import mock

import pytest
from axes.models import AccessAttempt
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from comun.models import EventoAuditoria
from comun.roles import Rol
from notificaciones.models import Notificacion
from usuarios.anonimizacion import correo_anonimo
from usuarios.eliminacion import eliminar_cuenta
from usuarios.models import CodigoVerificacion, Dispositivo2FA, Estado, RegistroAcceso, Usuario
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/eliminar-cuenta/"
LOGIN = "/api/v1/auth/login/"
REGISTRO = "/api/v1/auth/registro/"
PROTEGIDO = "/api/v1/auth/privacidad/aceptar/"
DATOS = {"password": PASSWORD_PRUEBA, "confirmacion": "ELIMINAR"}


def eliminar(api_client, usuario):
    api_client.force_authenticate(user=usuario)
    respuesta = api_client.post(URL, DATOS, format="json")
    api_client.force_authenticate(user=None)
    usuario.refresh_from_db()
    return respuesta


# Cuenta anonimizada

def test_nombre_correo_y_telefono_quedan_anonimizados(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com", first_name="Ana", last_name="López", telefono="+524431230001")
    assert eliminar(api_client, usuario).status_code == 200

    assert usuario.email == correo_anonimo(usuario)
    assert (usuario.first_name, usuario.last_name) == ("Usuario", "eliminado")
    assert usuario.telefono is None


def test_conserva_id_rol_y_fechas(api_client):
    usuario = UsuarioFactory(rol=Rol.CLIENTE)
    antes = (usuario.pk, usuario.rol, usuario.date_joined)
    eliminar(api_client, usuario)

    assert (usuario.pk, usuario.rol, usuario.date_joined) == antes


def test_la_cuenta_queda_inactiva(api_client):
    usuario = UsuarioFactory()
    eliminar(api_client, usuario)

    assert usuario.estado == Estado.INACTIVO
    assert usuario.is_active is False


# Sesiones

def test_la_contrasena_anterior_ya_no_sirve(api_client):
    usuario = UsuarioFactory()
    eliminar(api_client, usuario)

    assert not usuario.check_password(PASSWORD_PRUEBA)
    assert not usuario.has_usable_password()


def test_no_se_puede_iniciar_sesion_con_el_correo_original(api_client, llaves):
    UsuarioFactory(email="ana@ejemplo.com")
    usuario = Usuario.objects.get(email="ana@ejemplo.com")
    eliminar(api_client, usuario)

    respuesta = api_client.post(LOGIN, {"email": "ana@ejemplo.com", "password": PASSWORD_PRUEBA}, format="json")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "credenciales_invalidas"


def test_no_se_puede_iniciar_sesion_con_el_telefono_original(api_client, llaves):
    usuario = UsuarioFactory(telefono="+524431230002")
    eliminar(api_client, usuario)

    respuesta = api_client.post(LOGIN, {"email": "+524431230002", "password": PASSWORD_PRUEBA}, format="json")
    assert respuesta.status_code == 401


def test_el_token_de_acceso_deja_de_servir_y_no_se_puede_eliminar_dos_veces(api_client, llaves):
    UsuarioFactory(email="ana@ejemplo.com")
    login = api_client.post(LOGIN, {"email": "ana@ejemplo.com", "password": PASSWORD_PRUEBA}, format="json")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

    assert api_client.post(URL, DATOS, format="json").status_code == 200
    assert api_client.post(PROTEGIDO, {}, format="json").status_code == 401
    assert api_client.post(URL, DATOS, format="json").status_code == 401


def test_token_version_sube_una_sola_vez(api_client):
    usuario = UsuarioFactory()
    antes = usuario.token_version
    eliminar(api_client, usuario)

    assert usuario.token_version == antes + 1


def test_todos_los_refresh_tokens_quedan_en_la_lista_negra(api_client, llaves):
    usuario = UsuarioFactory()
    refrescos = [RefreshToken.for_user(usuario) for _ in range(3)]
    eliminar(api_client, usuario)

    assert OutstandingToken.objects.filter(user=usuario).count() == 3
    for refresco in refrescos:
        assert BlacklistedToken.objects.filter(token__jti=refresco["jti"]).exists()


# Credenciales y avisos

def test_borra_los_codigos_pendientes_y_el_segundo_factor(api_client):
    usuario = UsuarioFactory()
    CodigoVerificacion.objects.create(usuario=usuario, proposito="recuperacion", canal="correo", codigo_hash="x",
                                      expira_en="2099-01-01T00:00:00Z")
    Dispositivo2FA.objects.create(usuario=usuario, secreto_cifrado="x")
    eliminar(api_client, usuario)

    assert not CodigoVerificacion.objects.filter(usuario=usuario).exists()
    assert not Dispositivo2FA.objects.filter(usuario=usuario).exists()


def test_borra_las_notificaciones_pendientes_y_vacia_el_contenido_de_las_enviadas(api_client):
    usuario = UsuarioFactory()
    Notificacion.objects.create(destinatario=usuario, canal="correo", plantilla="bienvenida",
                                contexto={"nombre": "Ana"}, estado=Notificacion.ESTADO_PENDIENTE)
    Notificacion.objects.create(destinatario=usuario, canal="correo", plantilla="activacion",
                                contexto={"codigo": "123456"}, estado=Notificacion.ESTADO_ENVIADA)
    eliminar(api_client, usuario)

    assert not Notificacion.objects.filter(destinatario=usuario, estado=Notificacion.ESTADO_PENDIENTE).exists()
    assert Notificacion.objects.get(destinatario=usuario).contexto == {}


def test_borra_los_intentos_de_axes_del_correo_original(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    AccessAttempt.objects.create(username="ana@ejemplo.com", failures_since_start=2, ip_address="201.141.10.5",
                                 user_agent="x", http_accept="x", path_info="/")
    eliminar(api_client, usuario)

    assert not AccessAttempt.objects.filter(username__iexact="ana@ejemplo.com").exists()


# Registros relacionados

def test_conserva_el_historial_de_accesos_y_la_bitacora(api_client):
    usuario = UsuarioFactory()
    RegistroAcceso.objects.create(usuario=usuario, ip="201.141.10.5", dispositivo="Chrome", exitoso=True)
    EventoAuditoria.objects.create(usuario=usuario, accion="login")
    eliminar(api_client, usuario)

    assert RegistroAcceso.objects.filter(usuario=usuario).count() == 1
    assert EventoAuditoria.objects.filter(usuario=usuario, accion="login").count() == 1


def test_la_bitacora_registra_la_eliminacion_sin_datos_personales(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com", first_name="Ana", telefono="+524431230003")
    eliminar(api_client, usuario)

    evento = EventoAuditoria.objects.get(usuario=usuario, accion="cuenta_anonimizada")
    contenido = json.dumps(evento.detalles)
    assert "ana@ejemplo.com" not in contenido and "+524431230003" not in contenido


# Datos libres para volver a registrarse

def test_se_puede_registrar_de_nuevo_con_el_mismo_correo_y_telefono(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com", telefono="+524431230004")
    eliminar(api_client, usuario)

    datos = {
        "nombre": "Ana", "apellidos": "López", "correo": "ana@ejemplo.com", "telefono": "443 123 0004",
        "password": "Registro2026", "password_confirmacion": "Registro2026",
        "canal_preferido": "correo", "acepto_privacidad": True,
    }
    respuesta = api_client.post(REGISTRO, datos, format="json")

    assert respuesta.status_code == 201
    nueva = Usuario.objects.get(email="ana@ejemplo.com")
    assert nueva.pk != usuario.pk


# Todo o nada

def test_si_la_anonimizacion_falla_la_cuenta_queda_intacta():
    usuario = UsuarioFactory(email="ana@ejemplo.com", telefono="+524431230005")
    CodigoVerificacion.objects.create(usuario=usuario, proposito="recuperacion", canal="correo", codigo_hash="x",
                                      expira_en="2099-01-01T00:00:00Z")
    with mock.patch("usuarios.eliminacion.anonimizar_usuario", side_effect=RuntimeError("falla simulada")):
        with pytest.raises(RuntimeError):
            eliminar_cuenta(usuario)

    usuario.refresh_from_db()
    assert usuario.email == "ana@ejemplo.com" and usuario.telefono == "+524431230005"
    assert usuario.estado == Estado.ACTIVO
    assert CodigoVerificacion.objects.filter(usuario=usuario).exists()


def test_el_unico_administrador_conserva_todo(api_client):
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR, email="admin@ejemplo.com", telefono="+524431230006")
    CodigoVerificacion.objects.create(usuario=admin, proposito="recuperacion", canal="correo", codigo_hash="x",
                                      expira_en="2099-01-01T00:00:00Z")
    api_client.force_authenticate(user=admin)
    assert api_client.post(URL, DATOS, format="json").status_code == 403

    admin.refresh_from_db()
    assert admin.email == "admin@ejemplo.com" and admin.telefono == "+524431230006"
    assert admin.is_active and admin.has_usable_password()
    assert CodigoVerificacion.objects.filter(usuario=admin).exists()