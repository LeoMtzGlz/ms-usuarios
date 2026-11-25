"""t-17/st-151: Pruebas de HU-17 · edición correcta y duplicado rechazado.

Complementan las de st-149 y st-150 (usuarios/tests/test_edicion_usuario.py) con
los casos que faltaban:
- Edición correcta: el usuario puede iniciar sesión con su nuevo correo o teléfono.
- Duplicado rechazado: con el teléfono en otro formato, contra cuentas inactivas o
  pendientes, con el mensaje del catálogo, y sin guardar ningún otro cambio.
"""

import pytest

from comun.roles import Rol
from usuarios.models import Estado
from usuarios.serializers import CORREO_REGISTRADO, TELEFONO_REGISTRADO
from usuarios.tests.factories import PASSWORD_PRUEBA
from usuarios.tests.helpers_admin import api_de, crear_usuario

URL = "/api/v1/usuarios/{}/"
LOGIN = "/api/v1/auth/login/"


@pytest.fixture
def api_admin(db, llaves):
    return api_de(crear_usuario(Rol.ADMINISTRADOR))


@pytest.fixture
def operativo(db, llaves):
    return crear_usuario(Rol.OPERATIVO)


@pytest.fixture
def otro(db, llaves):
    return crear_usuario(Rol.CLIENTE)


def local(telefono):
    """+524431000001 → 4431000001 (formato de 10 dígitos que escribe una persona)."""
    return telefono.removeprefix("+52")


def login(api_client, identificador):
    return api_client.post(LOGIN, {"email": identificador, "password": PASSWORD_PRUEBA}, format="json")


# --- Edición correcta ---


@pytest.mark.django_db
class TestEdicionCorrecta:
    def test_inicia_sesion_con_el_correo_nuevo_y_no_con_el_anterior(self, api_admin, api_client, operativo):
        anterior = operativo.email
        r = api_admin.patch(URL.format(operativo.pk), {"correo": "nuevo.acceso@ejemplo.com"}, format="json")

        assert r.status_code == 200
        assert login(api_client, "nuevo.acceso@ejemplo.com").status_code == 200
        assert login(api_client, anterior).status_code == 401

    def test_inicia_sesion_con_el_telefono_nuevo_y_no_con_el_anterior(self, api_admin, api_client, operativo):
        anterior = operativo.telefono
        r = api_admin.patch(URL.format(operativo.pk), {"telefono": "443 999 8877"}, format="json")

        assert r.status_code == 200
        assert login(api_client, "+524439998877").status_code == 200
        assert login(api_client, anterior).status_code == 401

    def test_la_respuesta_trae_los_datos_editados(self, api_admin, operativo):
        cambios = {"nombre": "Ana", "apellidos": "Ruiz", "correo": "ana.ruiz@ejemplo.com", "telefono": "4437776655"}
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 200
        assert r.data["id"] == str(operativo.pk)
        assert (r.data["nombre"], r.data["apellidos"]) == ("Ana", "Ruiz")
        assert (r.data["correo"], r.data["telefono"]) == ("ana.ruiz@ejemplo.com", "+524437776655")

    def test_no_cambia_rol_ni_estado(self, api_admin, operativo):
        """Editar los datos no toca el rol ni el estado."""
        r = api_admin.patch(URL.format(operativo.pk), {"nombre": "Otro Nombre"}, format="json")

        assert r.status_code == 200
        operativo.refresh_from_db()
        assert operativo.rol == Rol.OPERATIVO
        assert operativo.estado == Estado.ACTIVO

    def test_rechaza_rol_y_estado_y_conserva_los_originales(self, api_admin, operativo):
        """Si se envían rol o estado, se rechaza todo y no cambia nada (HU-17, criterio 2)."""
        cambios = {"nombre": "No Se Guarda", "rol": Rol.ADMINISTRADOR, "estado": Estado.INACTIVO}
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 400
        assert {"rol", "estado"} <= set(r.data["campos"])
        operativo.refresh_from_db()
        assert operativo.rol == Rol.OPERATIVO
        assert operativo.estado == Estado.ACTIVO
        assert operativo.first_name != "No Se Guarda"

    def test_puede_reenviar_su_propio_telefono_en_otro_formato(self, api_admin, operativo):
        r = api_admin.patch(URL.format(operativo.pk), {"telefono": local(operativo.telefono)}, format="json")
        assert r.status_code == 200


# --- Duplicado rechazado ---


@pytest.mark.django_db
class TestDuplicadoRechazado:
    def test_correo_duplicado_usa_el_mensaje_del_catalogo(self, api_admin, operativo, otro):
        r = api_admin.patch(URL.format(operativo.pk), {"correo": otro.email}, format="json")

        assert r.status_code == 400
        assert r.data["codigo"] == "datos_invalidos"
        assert r.data["campos"]["correo"] == [CORREO_REGISTRADO]

    def test_telefono_duplicado_usa_el_mensaje_del_catalogo(self, api_admin, operativo, otro):
        r = api_admin.patch(URL.format(operativo.pk), {"telefono": otro.telefono}, format="json")

        assert r.status_code == 400
        assert r.data["campos"]["telefono"] == [TELEFONO_REGISTRADO]

    def test_telefono_de_otro_en_formato_local_se_rechaza(self, api_admin, operativo, otro):
        """El teléfono se normaliza antes de buscar duplicados."""
        r = api_admin.patch(URL.format(operativo.pk), {"telefono": local(otro.telefono)}, format="json")

        assert r.status_code == 400
        assert "telefono" in r.data["campos"]

    def test_correo_y_telefono_duplicados_se_reportan_juntos(self, api_admin, operativo, otro):
        cambios = {"correo": otro.email, "telefono": otro.telefono}
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 400
        assert {"correo", "telefono"} <= set(r.data["campos"])

    @pytest.mark.parametrize("estado", [Estado.INACTIVO, Estado.PENDIENTE])
    def test_correo_de_una_cuenta_no_activa_tambien_se_rechaza(self, api_admin, operativo, estado):
        inactiva = crear_usuario(Rol.CLIENTE, estado=estado)
        r = api_admin.patch(URL.format(operativo.pk), {"correo": inactiva.email}, format="json")

        assert r.status_code == 400
        assert "correo" in r.data["campos"]

    def test_con_un_duplicado_no_se_guarda_ningun_cambio(self, api_admin, operativo, otro):
        """Si un campo es duplicado, tampoco se guardan los demás campos válidos."""
        nombre, correo = operativo.first_name, operativo.email
        cambios = {"nombre": "No Se Guarda", "correo": otro.email}
        r = api_admin.patch(URL.format(operativo.pk), cambios, format="json")

        assert r.status_code == 400
        operativo.refresh_from_db()
        assert (operativo.first_name, operativo.email) == (nombre, correo)

    def test_el_otro_usuario_no_se_modifica(self, api_admin, operativo, otro):
        correo, telefono = otro.email, otro.telefono
        r = api_admin.patch(URL.format(operativo.pk), {"correo": otro.email, "telefono": otro.telefono}, format="json")

        assert r.status_code == 400
        otro.refresh_from_db()
        assert (otro.email, otro.telefono) == (correo, telefono)