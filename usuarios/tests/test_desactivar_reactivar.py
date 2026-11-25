"""t-18/st-153: POST /api/v1/usuarios/{id}/desactivar/ y /reactivar/ (HU-18).

Las pruebas de inicio de sesión y renovación de tokens después de desactivar
son de st-154.
"""

import json
import logging
import uuid

import pytest

from comun.roles import Rol
from usuarios.models import Estado, Usuario
from usuarios.tests.helpers_admin import api_de, crear_usuario

DESACTIVAR = "/api/v1/usuarios/{}/desactivar/"
REACTIVAR = "/api/v1/usuarios/{}/reactivar/"


@pytest.fixture
def admin(db, llaves):
    return crear_usuario(Rol.ADMINISTRADOR)


@pytest.fixture
def api_admin(admin):
    return api_de(admin)


@pytest.fixture
def usuario(db, llaves):
    return crear_usuario(Rol.CLIENTE)


def eventos_de_estado(caplog):
    registros = [json.loads(r.message) for r in caplog.records if r.name == "svc.auditoria"]
    return [e for e in registros if e["accion"] == "estado_cambiado"]


@pytest.mark.django_db
class TestDesactivar:
    def test_cambia_el_estado_a_inactivo(self, api_admin, usuario):
        r = api_admin.post(DESACTIVAR.format(usuario.pk))

        assert r.status_code == 200
        assert r.data == {"id": str(usuario.pk), "estado": Estado.INACTIVO}
        usuario.refresh_from_db()
        assert usuario.estado == Estado.INACTIVO
        assert usuario.is_active is False

    def test_cierra_sus_sesiones(self, api_admin, usuario):
        """HU-18, criterio 2: token_version += 1."""
        version = usuario.token_version
        api_admin.post(DESACTIVAR.format(usuario.pk))

        usuario.refresh_from_db()
        assert usuario.token_version == version + 1

    def test_nunca_borra_el_registro(self, api_admin, usuario):
        """HU-18, criterio 3."""
        api_admin.post(DESACTIVAR.format(usuario.pk))
        assert Usuario.objects.filter(pk=usuario.pk).exists()

    def test_el_admin_no_puede_desactivarse_a_si_mismo(self, api_admin, admin):
        """HU-18, criterio 4."""
        r = api_admin.post(DESACTIVAR.format(admin.pk))

        assert r.status_code == 400
        assert r.data["codigo"] == "datos_invalidos"
        admin.refresh_from_db()
        assert admin.estado == Estado.ACTIVO

    def test_desactivar_dos_veces_no_repite_el_cambio(self, api_admin, usuario):
        api_admin.post(DESACTIVAR.format(usuario.pk))
        usuario.refresh_from_db()
        version = usuario.token_version

        r = api_admin.post(DESACTIVAR.format(usuario.pk))

        assert r.status_code == 200
        usuario.refresh_from_db()
        assert usuario.token_version == version

    def test_registra_quien_lo_desactivo(self, api_admin, admin, usuario, caplog):
        with caplog.at_level(logging.INFO, logger="svc.auditoria"):
            api_admin.post(DESACTIVAR.format(usuario.pk))

        [evento] = eventos_de_estado(caplog)
        assert evento["usuario_id"] == str(usuario.pk)
        assert evento["detalles"]["nuevo"] == Estado.INACTIVO
        assert evento["detalles"]["por"] == str(admin.pk)


@pytest.mark.django_db
class TestReactivar:
    def test_cambia_el_estado_a_activo(self, api_admin, usuario):
        api_admin.post(DESACTIVAR.format(usuario.pk))
        r = api_admin.post(REACTIVAR.format(usuario.pk))

        assert r.status_code == 200
        assert r.data == {"id": str(usuario.pk), "estado": Estado.ACTIVO}
        usuario.refresh_from_db()
        assert usuario.estado == Estado.ACTIVO
        assert usuario.is_active is True

    def test_registra_quien_la_reactivo(self, api_admin, admin, usuario, caplog):
        api_admin.post(DESACTIVAR.format(usuario.pk))
        caplog.clear()  # solo interesa el evento de la reactivación
        with caplog.at_level(logging.INFO, logger="svc.auditoria"):
            api_admin.post(REACTIVAR.format(usuario.pk))

        [evento] = eventos_de_estado(caplog)
        assert evento["usuario_id"] == str(usuario.pk)
        assert evento["detalles"]["anterior"] == Estado.INACTIVO
        assert evento["detalles"]["nuevo"] == Estado.ACTIVO
        assert evento["detalles"]["por"] == str(admin.pk)

    def test_una_cuenta_pendiente_no_se_reactiva(self, api_admin):
        pendiente = crear_usuario(Rol.CLIENTE, estado=Estado.PENDIENTE)
        r = api_admin.post(REACTIVAR.format(pendiente.pk))

        assert r.status_code == 400
        pendiente.refresh_from_db()
        assert pendiente.estado == Estado.PENDIENTE

    def test_reactivar_una_cuenta_activa_no_cambia_nada(self, api_admin, usuario, caplog):
        with caplog.at_level(logging.INFO, logger="svc.auditoria"):
            r = api_admin.post(REACTIVAR.format(usuario.pk))

        assert r.status_code == 200
        assert eventos_de_estado(caplog) == []


@pytest.mark.django_db
class TestPermisosYRutas:
    @pytest.mark.parametrize("url", [DESACTIVAR, REACTIVAR])
    def test_sin_token_responde_401(self, api_client, usuario, url):
        assert api_client.post(url.format(usuario.pk)).status_code == 401

    @pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
    @pytest.mark.parametrize("url", [DESACTIVAR, REACTIVAR])
    def test_un_no_administrador_recibe_403(self, usuario, url, rol):
        r = api_de(crear_usuario(rol)).post(url.format(usuario.pk))

        assert r.status_code == 403
        usuario.refresh_from_db()
        assert usuario.estado == Estado.ACTIVO

    @pytest.mark.parametrize("url", [DESACTIVAR, REACTIVAR])
    def test_usuario_inexistente_responde_404(self, api_admin, url):
        assert api_admin.post(url.format(uuid.uuid4())).status_code == 404

    @pytest.mark.parametrize("url", [DESACTIVAR, REACTIVAR])
    def test_solo_acepta_post(self, api_admin, usuario, url):
        assert api_admin.get(url.format(usuario.pk)).status_code == 405