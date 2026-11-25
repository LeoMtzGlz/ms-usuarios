"""HU-15 / t-15/st-143: pruebas de los criterios de aceptación del alta de un operativo.

Complementa test_alta_usuario.py (st-140), test_contrasenas.py (st-141) y
test_alta_usuario_aviso.py (st-142): aquí se prueba el recorrido completo de la cuenta
creada y que la contraseña temporal no aparece en ninguna otra respuesta de la API.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from comun.roles import Rol
from usuarios.models import Zona
from usuarios.tests.helpers_admin import api_de, crear_usuario

pytestmark = pytest.mark.django_db

URL_ALTA = "/api/v1/usuarios/"
URL_DETALLE = "/api/v1/usuarios/{}/"
URL_LOGIN = "/api/v1/auth/login/"
URL_CAMBIAR = "/api/v1/auth/cambiar-password/"
URL_ACCESOS = "/api/v1/auth/accesos/"
URL_ACTIVAR_2FA = "/api/v1/auth/2fa/activar/"
# Endpoints que usan los permisos por defecto (IsAuthenticated + ContrasenaDefinitiva):
# representan al resto de la API para una cuenta con contraseña temporal.
ENDPOINTS_CON_PERMISOS_POR_DEFECTO = [("get", URL_ACCESOS), ("post", URL_ACTIVAR_2FA)]
CORREO = "luis.ramirez@ejemplo.com"
NUEVA = "Definitiva2026"


@pytest.fixture
def cliente_admin(llaves):
    return api_de(crear_usuario(Rol.ADMINISTRADOR))


def datos_validos(**cambios):
    zona, _ = Zona.objects.get_or_create(nombre="Centro", defaults={"activa": True})  # t-35/st-227
    datos = {
        "nombre": "Luis", "apellidos": "Ramírez Soto", "correo": CORREO, "telefono": "443 123 4567",
        "zona": zona.pk,
    }
    datos.update(cambios)
    return datos


def dar_de_alta(cliente_admin):
    r = cliente_admin.post(URL_ALTA, datos_validos(), format="json")
    assert r.status_code == 201, r.data
    return r.data


def iniciar_sesion(password):
    return APIClient().post(URL_LOGIN, {"email": CORREO, "password": password}, format="json")


def correos_de(respuesta):
    return [fila["correo"] for fila in respuesta.json()["results"]]


def cliente_con(acceso):
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return cliente


# --- CA3: la contraseña temporal se devuelve una sola vez -----------------------------------

def test_la_contrasena_no_aparece_en_el_listado(cliente_admin):
    temporal = dar_de_alta(cliente_admin)["contrasena_temporal"]

    for respuesta in (cliente_admin.get(URL_ALTA), cliente_admin.get(URL_ALTA, {"search": "Luis"})):
        assert respuesta.status_code == 200
        # Primero se confirma que la cuenta nueva sí está en la respuesta; si no, la prueba no probaría nada.
        assert CORREO in correos_de(respuesta)
        assert temporal not in respuesta.content.decode()


def test_la_contrasena_no_aparece_al_editar_la_cuenta(cliente_admin):
    alta = dar_de_alta(cliente_admin)

    r = cliente_admin.patch(URL_DETALLE.format(alta["id"]), {"nombre": "Luis Alberto"}, format="json")

    assert r.status_code == 200
    assert r.data["nombre"] == "Luis Alberto"
    assert alta["contrasena_temporal"] not in r.content.decode()
    assert "contrasena_temporal" not in r.data


# --- CA4: la cuenta queda activa, como Operativo y obligada a cambiar la contraseña ----------

def test_el_operativo_entra_con_la_contrasena_temporal(cliente_admin):
    temporal = dar_de_alta(cliente_admin)["contrasena_temporal"]

    r = iniciar_sesion(temporal)

    assert r.status_code == 200
    acceso = AccessToken(r.data["access"])
    assert acceso["rol"] == Rol.OPERATIVO
    assert acceso["debe_cambiar_password"] is True


@pytest.mark.parametrize("metodo,url", ENDPOINTS_CON_PERMISOS_POR_DEFECTO)
def test_con_la_contrasena_temporal_un_endpoint_con_permisos_por_defecto_responde_403(cliente_admin, metodo, url):
    temporal = dar_de_alta(cliente_admin)["contrasena_temporal"]
    operativo = cliente_con(iniciar_sesion(temporal).data["access"])

    r = getattr(operativo, metodo)(url, format="json")

    assert r.status_code == 403
    assert r.data["codigo"] == "debe_cambiar_password"


def test_al_cambiar_la_contrasena_temporal_ya_puede_trabajar(cliente_admin):
    temporal = dar_de_alta(cliente_admin)["contrasena_temporal"]
    operativo = cliente_con(iniciar_sesion(temporal).data["access"])

    cambio = operativo.post(
        URL_CAMBIAR,
        {"password_actual": temporal, "password_nueva": NUEVA, "password_confirmacion": NUEVA},
        format="json",
    )
    assert cambio.status_code == 200, cambio.data

    sesion = iniciar_sesion(NUEVA)
    assert sesion.status_code == 200
    assert AccessToken(sesion.data["access"])["debe_cambiar_password"] is False
    assert cliente_con(sesion.data["access"]).get(URL_ACCESOS).status_code == 200