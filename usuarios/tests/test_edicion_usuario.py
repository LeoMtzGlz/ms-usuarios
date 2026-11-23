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
class TestCamposProhibidos:
    @pytest.mark.parametrize("campo,valor", [
        ("password", "NuevaSegura1"),
        ("rol", Rol.ADMINISTRADOR),
        ("estado", "inactivo"),
        ("debe_cambiar_password", False),
        ("token_version", 99),
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


@pytest.mark.django_db
class TestDuplicados:
    def test_puede_reenviar_su_propio_correo(self, api_admin, operativo):
        r = api_admin.patch(URL.format(operativo.pk), {"email": operativo.email.upper()}, format="json")
        assert r.status_code == 200

    def test_correo_de_otro_rechazado_sin_importar_mayusculas(self, api_admin, operativo, cliente):
        r = api_admin.patch(URL.format(operativo.pk), {"email": cliente.email.upper()}, format="json")
        assert r.status_code == 400
        assert "email" in r.data["campos"]

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