"""HU-12 / ST-118: contraseña temporal, de punta a punta con los endpoints reales.

Criterios de HU-12:
  - Con debe_cambiar_password, cualquier endpoint distinto de cambiar-password responde 403 debe_cambiar_password.
  - Al cambiarla, el campo pasa a falso y se emiten tokens nuevos.

test_contrasena_definitiva.py (T-13) prueba el permiso con vistas de prueba y test_cambiar_password.py
(ST-117) prueba el método del modelo. Aquí se usan el login, el cambio y los endpoints de verdad.
"""
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"
RENOVAR = "/api/v1/auth/token/renovar/"
CAMBIAR = "/api/v1/auth/cambiar-password/"
NUEVA = "NuevaClave2026"

# Endpoints protegidos reales, distintos de cambiar-password
PROTEGIDOS = [
    ("get", "/api/v1/auth/accesos/"),
    ("post", "/api/v1/auth/2fa/activar/"),
    ("post", "/api/v1/auth/2fa/confirmar/"),
    ("post", "/api/v1/auth/2fa/desactivar/"),
]


@pytest.fixture
def temporal(db):
    return UsuarioFactory(email="temporal@ejemplo.com", debe_cambiar_password=True)


def iniciar_sesion(api_client, email, password=PASSWORD_PRUEBA):
    respuesta = api_client.post(LOGIN, {"email": email, "password": password}, format="json")
    api_client.credentials()
    return respuesta


def con_token(api_client, access):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")


def cambiar(api_client, access, **cambios):
    con_token(api_client, access)
    datos = {"password_actual": PASSWORD_PRUEBA, "password_nueva": NUEVA, "password_confirmacion": NUEVA}
    datos.update(cambios)
    return api_client.post(CAMBIAR, datos, format="json")


def llamar(api_client, metodo, ruta):
    return getattr(api_client, metodo)(ruta, {}, format="json") if metodo == "post" else api_client.get(ruta)


# Con contraseña temporal

def test_el_login_con_contrasena_temporal_funciona_y_marca_el_token(api_client, llaves, temporal):
    respuesta = iniciar_sesion(api_client, temporal.email)

    assert respuesta.status_code == 200
    assert AccessToken(respuesta.json()["access"])["debe_cambiar_password"] is True


@pytest.mark.parametrize("metodo, ruta", PROTEGIDOS)
def test_con_contrasena_temporal_los_demas_endpoints_responden_403(api_client, llaves, temporal, metodo, ruta):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    con_token(api_client, access)
    respuesta = llamar(api_client, metodo, ruta)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"


def test_con_contrasena_temporal_cambiar_password_si_funciona(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    assert cambiar(api_client, access).status_code == 200


def test_con_contrasena_temporal_se_puede_renovar_la_sesion_pero_sigue_marcada(api_client, llaves, temporal):
    refresh = iniciar_sesion(api_client, temporal.email).json()["refresh"]
    respuesta = api_client.post(RENOVAR, {"refresh": refresh}, format="json")

    assert respuesta.status_code == 200
    assert AccessToken(respuesta.json()["access"])["debe_cambiar_password"] is True


def test_un_cambio_fallido_no_quita_la_restriccion(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    assert cambiar(api_client, access, password_actual="Incorrecta123").status_code == 400

    temporal.refresh_from_db()
    assert temporal.debe_cambiar_password is True
    con_token(api_client, access)
    assert api_client.get("/api/v1/auth/accesos/").status_code == 403


# Después del cambio

def test_al_cambiarla_el_campo_pasa_a_falso(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    cambiar(api_client, access)

    temporal.refresh_from_db()
    assert temporal.debe_cambiar_password is False
    assert temporal.check_password(NUEVA)


def test_al_cambiarla_se_emiten_tokens_nuevos_ya_sin_la_marca(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    respuesta = cambiar(api_client, access)
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["access"] and cuerpo["refresh"]
    assert AccessToken(cuerpo["access"])["debe_cambiar_password"] is False
    assert cuerpo["access"] != access


@pytest.mark.parametrize("metodo, ruta", PROTEGIDOS)
def test_con_el_token_nuevo_los_demas_endpoints_ya_no_responden_403_de_contrasena(
    api_client, llaves, temporal, metodo, ruta
):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    nuevo = cambiar(api_client, access).json()["access"]
    con_token(api_client, nuevo)
    respuesta = llamar(api_client, metodo, ruta)

    assert respuesta.status_code != 403 or respuesta.json()["codigo"] != "debe_cambiar_password"


def test_con_el_token_nuevo_el_historial_funciona(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    nuevo = cambiar(api_client, access).json()["access"]
    con_token(api_client, nuevo)

    assert api_client.get("/api/v1/auth/accesos/").status_code == 200


def test_el_access_temporal_anterior_sigue_restringido(api_client, llaves, temporal):
    # El access es corto y sin estado: no se revoca, pero conserva la marca y sigue dando 403.
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    cambiar(api_client, access)
    con_token(api_client, access)
    respuesta = api_client.get("/api/v1/auth/accesos/")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"


def test_el_refresh_temporal_anterior_ya_no_sirve(api_client, llaves, temporal):
    sesion = iniciar_sesion(api_client, temporal.email).json()
    cambiar(api_client, sesion["access"])
    api_client.credentials()

    assert api_client.post(RENOVAR, {"refresh": sesion["refresh"]}, format="json").status_code == 401


def test_el_refresh_nuevo_renueva_sin_la_marca(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    refresh_nuevo = cambiar(api_client, access).json()["refresh"]
    api_client.credentials()
    respuesta = api_client.post(RENOVAR, {"refresh": refresh_nuevo}, format="json")

    assert respuesta.status_code == 200
    assert AccessToken(respuesta.json()["access"])["debe_cambiar_password"] is False


def test_la_contrasena_temporal_ya_no_inicia_sesion_y_la_nueva_si(api_client, llaves, temporal):
    access = iniciar_sesion(api_client, temporal.email).json()["access"]
    cambiar(api_client, access)

    assert iniciar_sesion(api_client, temporal.email, PASSWORD_PRUEBA).status_code == 401
    nuevo_login = iniciar_sesion(api_client, temporal.email, NUEVA)
    assert nuevo_login.status_code == 200
    assert AccessToken(nuevo_login.json()["access"])["debe_cambiar_password"] is False


# Contraseña definitiva

@pytest.mark.parametrize("metodo, ruta", PROTEGIDOS)
def test_con_contrasena_definitiva_nunca_responde_403_de_contrasena_temporal(api_client, llaves, metodo, ruta):
    usuario = UsuarioFactory(debe_cambiar_password=False)
    access = iniciar_sesion(api_client, usuario.email).json()["access"]
    con_token(api_client, access)
    respuesta = llamar(api_client, metodo, ruta)

    assert respuesta.status_code != 403 or respuesta.json()["codigo"] != "debe_cambiar_password"


def test_sin_token_sigue_respondiendo_401_y_no_403(api_client, llaves):
    assert api_client.get("/api/v1/auth/accesos/").status_code == 401