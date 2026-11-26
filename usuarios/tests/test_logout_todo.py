"""Pruebas de HU-09/ST-99: cerrar sesión en todos los dispositivos (ST-98).

Cada "dispositivo" es un APIClient distinto con su propio login. Firman con las llaves
temporales del fixture `llaves` de conftest.py.
"""
import pytest
from rest_framework.test import APIClient

from comun.models import EventoAuditoria

from .factories import PASSWORD_PRUEBA

pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
URL_RENOVAR = "/api/v1/auth/token/renovar/"
URL_LOGOUT_TODO = "/api/v1/auth/logout-todo/"


def _iniciar_sesion(usuario):
    """Nuevo dispositivo: cliente propio, autenticado con el access de su login. Devuelve (cliente, refresh)."""
    cliente = APIClient()
    login = cliente.post(URL_LOGIN, {"email": usuario.email, "password": PASSWORD_PRUEBA}, format="json")
    assert login.status_code == 200, login.data
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return cliente, login.data["refresh"]


def _renovar(refresh):
    """Intenta renovar desde un cliente sin sesión, como lo haría cualquier dispositivo."""
    return APIClient().post(URL_RENOVAR, {"refresh": refresh}, format="json")


def _logout_todo(cliente):
    return cliente.post(URL_LOGOUT_TODO, format="json")


def test_el_refresh_de_otro_dispositivo_deja_de_renovar(usuario, llaves):
    dispositivo_a, _ = _iniciar_sesion(usuario)
    _, refresh_b = _iniciar_sesion(usuario)

    assert _logout_todo(dispositivo_a).status_code == 200

    respuesta = _renovar(refresh_b)
    assert respuesta.status_code == 401
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "access" not in cuerpo and "refresh" not in cuerpo


def test_el_refresh_del_propio_dispositivo_tampoco_renueva(usuario, llaves):
    dispositivo_a, refresh_a = _iniciar_sesion(usuario)

    assert _logout_todo(dispositivo_a).status_code == 200

    respuesta = _renovar(refresh_a)
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_todo_incrementa_token_version_en_uno(usuario, llaves):
    version_inicial = usuario.token_version
    dispositivo_a, _ = _iniciar_sesion(usuario)

    _logout_todo(dispositivo_a)

    usuario.refresh_from_db()
    assert usuario.token_version == version_inicial + 1


def test_logout_todo_se_registra_en_la_bitacora(usuario, llaves):
    dispositivo_a, _ = _iniciar_sesion(usuario)

    _logout_todo(dispositivo_a)

    evento = EventoAuditoria.objects.get(accion="logout_todo")
    assert evento.usuario == usuario
    assert evento.resultado == "ok"


def test_sin_autenticacion_responde_401_y_no_cambia_token_version(api_client, usuario, llaves):
    version_inicial = usuario.token_version

    respuesta = _logout_todo(api_client)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"
    usuario.refresh_from_db()
    assert usuario.token_version == version_inicial
    assert not EventoAuditoria.objects.filter(accion="logout_todo").exists()


def test_un_login_nuevo_despues_de_logout_todo_si_renueva(usuario, llaves):
    dispositivo_a, _ = _iniciar_sesion(usuario)
    _logout_todo(dispositivo_a)

    _, refresh_nuevo = _iniciar_sesion(usuario)
    respuesta = _renovar(refresh_nuevo)

    assert respuesta.status_code == 200, respuesta.data
    assert "access" in respuesta.data and "refresh" in respuesta.data


def test_logout_todo_dos_veces_no_falla_y_sube_token_version_en_dos(usuario, llaves):
    version_inicial = usuario.token_version
    dispositivo_a, _ = _iniciar_sesion(usuario)

    # El access de 15 minutos sigue siendo válido: JWTAuthentication no revisa token_version
    assert _logout_todo(dispositivo_a).status_code == 200
    assert _logout_todo(dispositivo_a).status_code == 200

    usuario.refresh_from_db()
    assert usuario.token_version == version_inicial + 2
