"""HU-17 / t-17/st-149: PATCH /api/v1/usuarios/{id}/ (edición por el administrador)."""
import uuid

import pytest

from comun.roles import Rol
from usuarios.tests.helpers_admin import api_de, crear_usuario

URL = "/api/v1/usuarios/{}/"


@pytest.fixture
def admin(db, llaves):
    return crear_usuario(Rol.ADMINISTRADOR)


@pytest.fixture
def operativo(db, llaves):
    return crear_usuario(Rol.OPERATIVO)


@pytest.fixture
def cliente(db, llaves):
    return crear_usuario(Rol.CLIENTE)


@pytest.fixture
def api_admin(admin):
    return api_de(admin)


@pytest.mark.django_db
class TestEdicion:
    def test_edita_nombre_apellidos_correo_y_telefono(self, api_admin, operativo):
        cambios = {
            "nombre": "Luis Alberto",
            "apellidos": "Pérez Soto",
            "correo": "luis.alberto@ejemplo.com",
            "telefono": "+524431112233",
        }
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 200
        assert r.data["correo"] == "luis.alberto@ejemplo.com"
        operativo.refresh_from_db()
        assert operativo.first_name == "Luis Alberto"
        assert operativo.last_name == "Pérez Soto"
        assert operativo.email == "luis.alberto@ejemplo.com"
        assert operativo.telefono == "+524431112233"

    def test_edicion_parcial_cambia_solo_lo_enviado(self, api_admin, operativo):
        correo, telefono = operativo.email, operativo.telefono
        r = api_admin.patch(URL.format(operativo.pk), {"nombre": "Solo Nombre"}, format="json")

        assert r.status_code == 200
        operativo.refresh_from_db()
        assert operativo.first_name == "Solo Nombre"
        assert operativo.email == correo
        assert operativo.telefono == telefono

    def test_normaliza_correo_y_telefono(self, api_admin, operativo):
        cambios = {"correo": "  Nuevo.Correo@Ejemplo.COM ", "telefono": "443 111 2233"}
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 200
        operativo.refresh_from_db()
        assert operativo.email == "nuevo.correo@ejemplo.com"
        assert operativo.telefono == "+524431112233"

    def test_la_respuesta_no_incluye_la_contrasena(self, api_admin, operativo):
        r = api_admin.patch(URL.format(operativo.pk), {"nombre": "X"}, format="json")
        assert "password" not in r.data
        assert "contrasena_temporal" not in r.data


@pytest.mark.django_db
class TestCamposProhibidos:
    @pytest.mark.parametrize("campo,valor", [
        ("password", "NuevaSegura1"),
        ("rol", Rol.ADMINISTRADOR),
        ("estado", "inactivo"),
        ("debe_cambiar_password", False),
        ("token_version", 99),
        ("email", "otro@ejemplo.com"),  # el correo se edita como "correo", igual que en el alta
    ])
    def test_rechaza_campo_no_editable(self, api_admin, operativo, campo, valor):
        r = api_admin.patch(URL.format(operativo.pk), {campo: valor}, format="json")
        assert r.status_code == 400
        assert campo in r.data["campos"]
        operativo.refresh_from_db()
        assert operativo.rol == Rol.OPERATIVO

    def test_put_no_esta_permitido(self, api_admin, operativo):
        r = api_admin.put(URL.format(operativo.pk), {"nombre": "X"}, format="json")
        assert r.status_code == 405

    def test_get_en_el_detalle_no_esta_permitido(self, api_admin, operativo):
        r = api_admin.get(URL.format(operativo.pk))
        assert r.status_code == 405

    def test_patch_sin_id_no_esta_permitido(self, api_admin):
        r = api_admin.patch("/api/v1/usuarios/", {"nombre": "X"}, format="json")
        assert r.status_code == 405


@pytest.mark.django_db
class TestDuplicados:
    def test_puede_reenviar_su_propio_correo(self, api_admin, operativo):
        r = api_admin.patch(URL.format(operativo.pk), {"correo": operativo.email.upper()}, format="json")
        assert r.status_code == 200

    def test_correo_de_otro_rechazado_sin_importar_mayusculas(self, api_admin, operativo, cliente):
        r = api_admin.patch(URL.format(operativo.pk), {"correo": cliente.email.upper()}, format="json")
        assert r.status_code == 400
        assert "correo" in r.data["campos"]

    def test_telefono_de_otro_rechazado(self, api_admin, operativo, cliente):
        r = api_admin.patch(URL.format(operativo.pk), {"telefono": cliente.telefono}, format="json")
        assert r.status_code == 400
        assert "telefono" in r.data["campos"]


@pytest.mark.django_db
class TestPermisos:
    def test_no_admin_recibe_403(self, cliente, operativo):
        r = api_de(cliente).patch(URL.format(operativo.pk), {"nombre": "X"}, format="json")
        assert r.status_code == 403

    def test_sin_token_recibe_401(self, api_client, operativo):
        r = api_client.patch(URL.format(operativo.pk), {"nombre": "X"}, format="json")
        assert r.status_code == 401

    def test_usuario_inexistente_responde_404(self, api_admin):
        r = api_admin.patch(URL.format(uuid.uuid4()), {"nombre": "X"}, format="json")
        assert r.status_code == 404