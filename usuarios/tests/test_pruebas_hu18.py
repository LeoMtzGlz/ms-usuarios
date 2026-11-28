"""t-18/st-154: pruebas de la HU-18 (desactivar o reactivar una cuenta).

Inactivo no entra; su refresh no renueva; reactivado entra.
La cuenta se desactiva y reactiva con los endpoints reales de st-153.
"""

import pytest

from comun.roles import Rol
from usuarios.models import Estado, RegistroAcceso
from usuarios.tests.factories import PASSWORD_PRUEBA
from usuarios.tests.helpers_admin import api_de, crear_usuario

LOGIN = "/api/v1/auth/login/"
RENOVAR = "/api/v1/auth/token/renovar/"
PROTEGIDO = "/api/v1/auth/accesos/"
DESACTIVAR = "/api/v1/usuarios/{}/desactivar/"
REACTIVAR = "/api/v1/usuarios/{}/reactivar/"


@pytest.fixture
def api_admin(db, llaves):
    return api_de(crear_usuario(Rol.ADMINISTRADOR))


@pytest.fixture
def usuario(db, llaves):
    return crear_usuario(Rol.CLIENTE)


def desactivar(api_admin, usuario):
    """Desactiva con el endpoint de st-153 y comprueba que de verdad quedó inactivo."""
    r = api_admin.post(DESACTIVAR.format(usuario.pk))
    assert r.status_code == 200, r.data
    usuario.refresh_from_db()
    assert usuario.estado == Estado.INACTIVO
    assert usuario.is_active is False


def reactivar(api_admin, usuario):
    """Reactiva con el endpoint de st-153 y comprueba que de verdad quedó activo."""
    r = api_admin.post(REACTIVAR.format(usuario.pk))
    assert r.status_code == 200, r.data
    usuario.refresh_from_db()
    assert usuario.estado == Estado.ACTIVO
    assert usuario.is_active is True


def iniciar_sesion(api_client, usuario):
    return api_client.post(LOGIN, {"email": usuario.email, "password": PASSWORD_PRUEBA}, format="json")


def renovar(api_client, refresh):
    return api_client.post(RENOVAR, {"refresh": refresh}, format="json")


def consultar_con(api_client, access):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    respuesta = api_client.get(PROTEGIDO)
    api_client.credentials()
    return respuesta


@pytest.mark.django_db
class TestInactivoNoEntra:
    def test_el_login_responde_cuenta_inactiva(self, api_client, api_admin, usuario):
        desactivar(api_admin, usuario)

        r = iniciar_sesion(api_client, usuario)

        assert r.status_code == 403
        assert r.data["codigo"] == "cuenta_inactiva"
        assert "access" not in r.data
        assert "refresh" not in r.data

    def test_el_intento_queda_registrado_como_fallido(self, api_client, api_admin, usuario):
        desactivar(api_admin, usuario)

        iniciar_sesion(api_client, usuario)

        acceso = RegistroAcceso.objects.filter(usuario=usuario).latest("fecha")
        assert acceso.exitoso is False

    def test_su_access_anterior_ya_no_sirve(self, api_client, api_admin, usuario):
        access = iniciar_sesion(api_client, usuario).data["access"]
        assert consultar_con(api_client, access).status_code == 200

        desactivar(api_admin, usuario)

        assert consultar_con(api_client, access).status_code == 401


@pytest.mark.django_db
class TestRefreshNoRenueva:
    def test_su_refresh_ya_no_renueva(self, api_client, api_admin, usuario):
        refresh = iniciar_sesion(api_client, usuario).data["refresh"]

        desactivar(api_admin, usuario)
        r = renovar(api_client, refresh)

        assert r.status_code == 401
        assert r.data["codigo"] == "token_invalido"
        assert "access" not in r.data

    def test_el_refresh_anterior_sigue_rechazado_despues_de_reactivar(self, api_client, api_admin, usuario):
        """Desactivar cierra las sesiones para siempre: reactivar no revive los tokens viejos."""
        refresh = iniciar_sesion(api_client, usuario).data["refresh"]

        desactivar(api_admin, usuario)
        reactivar(api_admin, usuario)
        r = renovar(api_client, refresh)

        assert r.status_code == 401
        assert r.data["codigo"] == "token_invalido"


@pytest.mark.django_db
class TestReactivadoEntra:
    def test_el_login_entrega_los_tokens(self, api_client, api_admin, usuario):
        desactivar(api_admin, usuario)
        reactivar(api_admin, usuario)

        r = iniciar_sesion(api_client, usuario)

        assert r.status_code == 200
        assert r.data["access"]
        assert r.data["refresh"]
        assert r.data["usuario"]["id"] == str(usuario.pk)

    def test_su_access_nuevo_si_sirve(self, api_client, api_admin, usuario):
        desactivar(api_admin, usuario)
        reactivar(api_admin, usuario)

        access = iniciar_sesion(api_client, usuario).data["access"]

        assert consultar_con(api_client, access).status_code == 200

    def test_su_refresh_nuevo_si_renueva(self, api_client, api_admin, usuario):
        desactivar(api_admin, usuario)
        reactivar(api_admin, usuario)

        refresh = iniciar_sesion(api_client, usuario).data["refresh"]
        r = renovar(api_client, refresh)

        assert r.status_code == 200
        assert r.data["access"]
        assert r.data["refresh"]