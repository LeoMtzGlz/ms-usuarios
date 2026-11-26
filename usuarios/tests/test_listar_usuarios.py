"""HU-16 / ST-145: pruebas de GET /api/v1/usuarios/ (listar, buscar y filtrar)."""
from datetime import timedelta

import pytest
from axes.models import AccessAttempt
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from comun.roles import Rol
from usuarios.models import Estado
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/usuarios/"
CAMPOS = {"id", "nombre", "apellidos", "correo", "telefono", "rol", "estado", "bloqueada", "ultimo_acceso"}


def cliente_como(api_client, usuario, **claims):
    """Autentica con un token que lleva el claim `rol`, como el que emite usuarios/tokens.py."""
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    for nombre, valor in claims.items():
        acceso[nombre] = valor
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api_client


@pytest.fixture(autouse=True)
def hash_rapido(settings):
    """Estas pruebas crean decenas de usuarios; con Argon2 (lento a propósito) tardarían un minuto.

    Ninguna revisa contraseñas: el hash real de Argon2 lo cubren test_hash_password y test_alta_usuario.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def correos(respuesta):
    return [fila["correo"] for fila in respuesta.json()["results"]]


@pytest.fixture
def admin(llaves):
    return UsuarioFactory(
        rol=Rol.ADMINISTRADOR, first_name="Zeta", last_name="Admin", email="zeta.admin@ejemplo.com",
        telefono="+524430000001",
    )


@pytest.fixture
def cliente_admin(api_client, admin):
    return cliente_como(api_client, admin)


@pytest.fixture
def equipo(admin):
    """Cuatro personas con nombres fáciles de buscar, además del administrador."""
    return {
        "ana": UsuarioFactory(
            first_name="Ana", last_name="Blanco", email="ana.blanco@ejemplo.com",
            telefono="+524431110001", rol=Rol.OPERATIVO, estado=Estado.ACTIVO,
        ),
        "beto": UsuarioFactory(
            first_name="Beto", last_name="Campos", email="beto.campos@ejemplo.com",
            telefono="+524432220002", rol=Rol.OPERATIVO, estado=Estado.INACTIVO,
        ),
        "carla": UsuarioFactory(
            first_name="Carla", last_name="Blanco", email="carla@otro.org",
            telefono="+524433330003", rol=Rol.CLIENTE, estado=Estado.ACTIVO,
        ),
        "dario": UsuarioFactory(
            first_name="Dario", last_name="Duran", email="dario.duran@ejemplo.com",
            telefono="+524434440004", rol=Rol.CLIENTE, estado=Estado.PENDIENTE,
        ),
    }


def intento_de_acceso(username, fallos, hace=timedelta(0)):
    """Registro de django-axes: `fallos` intentos fallidos de `username`, de hace `hace`."""
    intento = AccessAttempt.objects.create(
        username=username, ip_address="10.0.0.1", user_agent="pytest", http_accept="*/*",
        path_info="/api/v1/auth/login/", get_data="", post_data="", failures_since_start=fallos,
    )
    AccessAttempt.objects.filter(pk=intento.pk).update(attempt_time=timezone.now() - hace)
    return intento


# --- Qué devuelve --------------------------------------------------------------------


def test_lista_los_campos_del_criterio_de_aceptacion(cliente_admin, equipo):
    respuesta = cliente_admin.get(URL)

    assert respuesta.status_code == 200
    fila = next(f for f in respuesta.json()["results"] if f["correo"] == "ana.blanco@ejemplo.com")
    assert set(fila) == CAMPOS
    assert fila["nombre"] == "Ana"
    assert fila["apellidos"] == "Blanco"
    assert fila["telefono"] == "+524431110001"
    assert fila["rol"] == Rol.OPERATIVO
    assert fila["estado"] == Estado.ACTIVO
    assert fila["bloqueada"] is False
    assert fila["ultimo_acceso"] is None


def test_no_expone_datos_sensibles(cliente_admin, equipo):
    for fila in cliente_admin.get(URL).json()["results"]:
        for prohibido in ("password", "token_version", "is_staff", "is_superuser", "debe_cambiar_password"):
            assert prohibido not in fila


def test_ultimo_acceso_muestra_la_fecha_del_ultimo_login(cliente_admin, equipo):
    ahora = timezone.now()
    equipo["ana"].last_login = ahora
    equipo["ana"].save(update_fields=["last_login"])

    fila = next(f for f in cliente_admin.get(URL).json()["results"] if f["correo"] == "ana.blanco@ejemplo.com")

    assert fila["ultimo_acceso"] is not None
    assert fila["ultimo_acceso"].startswith(ahora.astimezone().strftime("%Y-"))


def test_incluye_a_todos_los_usuarios(cliente_admin, equipo):
    cuerpo = cliente_admin.get(URL).json()

    assert cuerpo["count"] == 5  # cuatro del equipo + el administrador


def test_ordena_por_nombre_apellidos_y_correo(cliente_admin, equipo):
    assert correos(cliente_admin.get(URL)) == [
        "ana.blanco@ejemplo.com",
        "beto.campos@ejemplo.com",
        "carla@otro.org",
        "dario.duran@ejemplo.com",
        "zeta.admin@ejemplo.com",
    ]


# --- Paginación ----------------------------------------------------------------------


def test_pagina_de_20_en_20(cliente_admin):
    for n in range(24):
        UsuarioFactory(first_name=f"Persona{n:02d}", email=f"persona{n:02d}@ejemplo.com")  # + el admin = 25

    primera = cliente_admin.get(URL).json()
    segunda = cliente_admin.get(URL, {"page": 2}).json()

    assert primera["count"] == 25
    assert len(primera["results"]) == 20
    assert primera["previous"] is None
    assert primera["next"] is not None
    assert len(segunda["results"]) == 5
    assert segunda["next"] is None


def test_las_paginas_no_repiten_ni_saltan_usuarios(cliente_admin):
    for n in range(24):
        UsuarioFactory(first_name=f"Persona{n:02d}", email=f"persona{n:02d}@ejemplo.com")

    vistos = correos(cliente_admin.get(URL)) + correos(cliente_admin.get(URL, {"page": 2}))

    assert len(vistos) == 25
    assert len(set(vistos)) == 25


def test_el_cliente_no_puede_cambiar_el_tamano_de_pagina(cliente_admin):
    for n in range(24):
        UsuarioFactory(email=f"persona{n:02d}@ejemplo.com")

    assert len(cliente_admin.get(URL, {"page_size": 100}).json()["results"]) == 20


def test_una_pagina_fuera_de_rango_responde_404(cliente_admin, equipo):
    assert cliente_admin.get(URL, {"page": 99}).status_code == 404


def test_la_busqueda_tambien_se_pagina(cliente_admin):
    for n in range(22):
        UsuarioFactory(first_name="Lupe", email=f"lupe{n:02d}@ejemplo.com")

    cuerpo = cliente_admin.get(URL, {"search": "lupe"}).json()

    assert cuerpo["count"] == 22
    assert len(cuerpo["results"]) == 20


# --- Búsqueda ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("busqueda", "esperados"),
    [
        ("Beto", ["beto.campos@ejemplo.com"]),                       # por nombre
        ("Campos", ["beto.campos@ejemplo.com"]),                     # por apellido
        ("Blanco", ["ana.blanco@ejemplo.com", "carla@otro.org"]),    # varios resultados
        ("Carla Blanco", ["carla@otro.org"]),                        # nombre completo: cada palabra debe aparecer
        ("otro.org", ["carla@otro.org"]),                            # por correo
        ("dario.duran", ["dario.duran@ejemplo.com"]),                # por parte del correo
        ("4432220002", ["beto.campos@ejemplo.com"]),                 # por teléfono
        ("+52443333", ["carla@otro.org"]),                           # por inicio del teléfono
    ],
)
def test_busca_por_nombre_correo_o_telefono(cliente_admin, equipo, busqueda, esperados):
    assert correos(cliente_admin.get(URL, {"search": busqueda})) == esperados


@pytest.mark.parametrize("busqueda", ["BETO", "beto", "BeTo"])
def test_la_busqueda_ignora_mayusculas(cliente_admin, equipo, busqueda):
    assert correos(cliente_admin.get(URL, {"search": busqueda})) == ["beto.campos@ejemplo.com"]


def test_busqueda_sin_coincidencias_responde_lista_vacia(cliente_admin, equipo):
    cuerpo = cliente_admin.get(URL, {"search": "nadie"}).json()

    assert cuerpo["count"] == 0
    assert cuerpo["results"] == []


def test_todas_las_palabras_de_la_busqueda_deben_coincidir(cliente_admin, equipo):
    assert correos(cliente_admin.get(URL, {"search": "Ana Campos"})) == []


def test_busqueda_vacia_devuelve_todos(cliente_admin, equipo):
    assert cliente_admin.get(URL, {"search": ""}).json()["count"] == 5


# --- Filtros -------------------------------------------------------------------------


def test_filtra_por_rol(cliente_admin, equipo):
    assert correos(cliente_admin.get(URL, {"rol": "operativo"})) == [
        "ana.blanco@ejemplo.com",
        "beto.campos@ejemplo.com",
    ]


@pytest.mark.parametrize(
    ("estado", "esperados"),
    [
        ("inactivo", ["beto.campos@ejemplo.com"]),
        ("pendiente", ["dario.duran@ejemplo.com"]),
        ("activo", ["ana.blanco@ejemplo.com", "carla@otro.org", "zeta.admin@ejemplo.com"]),
    ],
)
def test_filtra_por_estado(cliente_admin, equipo, estado, esperados):
    assert correos(cliente_admin.get(URL, {"estado": estado})) == esperados


def test_combina_rol_y_estado(cliente_admin, equipo):
    assert correos(cliente_admin.get(URL, {"rol": "cliente", "estado": "activo"})) == ["carla@otro.org"]


def test_combina_busqueda_y_filtros(cliente_admin, equipo):
    assert correos(cliente_admin.get(URL, {"search": "Blanco", "rol": "operativo"})) == [
        "ana.blanco@ejemplo.com"
    ]


def test_un_filtro_vacio_se_ignora(cliente_admin, equipo):
    assert cliente_admin.get(URL, {"rol": "", "estado": ""}).json()["count"] == 5


@pytest.mark.parametrize("parametros", [{"rol": "jefe"}, {"estado": "dormido"}])
def test_un_valor_de_filtro_inexistente_responde_400(cliente_admin, equipo, parametros):
    respuesta = cliente_admin.get(URL, parametros)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


# --- Cuenta bloqueada ----------------------------------------------------------------


def fila_de(cliente, correo):
    return next(f for f in cliente.get(URL).json()["results"] if f["correo"] == correo)


def test_una_cuenta_con_bloqueo_vigente_aparece_bloqueada(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso("ana.blanco@ejemplo.com", settings.AXES_FAILURE_LIMIT)

    assert fila_de(cliente_admin, "ana.blanco@ejemplo.com")["bloqueada"] is True
    assert fila_de(cliente_admin, "beto.campos@ejemplo.com")["bloqueada"] is False


def test_el_correo_del_intento_se_compara_sin_importar_mayusculas(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso("Ana.Blanco@EJEMPLO.com", settings.AXES_FAILURE_LIMIT)

    assert fila_de(cliente_admin, "ana.blanco@ejemplo.com")["bloqueada"] is True


def test_tambien_cuenta_el_intento_hecho_con_el_telefono(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso("+524432220002", settings.AXES_FAILURE_LIMIT)

    assert fila_de(cliente_admin, "beto.campos@ejemplo.com")["bloqueada"] is True


def test_con_menos_fallos_que_el_limite_no_esta_bloqueada(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso("ana.blanco@ejemplo.com", settings.AXES_FAILURE_LIMIT - 1)

    assert fila_de(cliente_admin, "ana.blanco@ejemplo.com")["bloqueada"] is False


def test_pasado_el_tiempo_de_espera_deja_de_estar_bloqueada(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso(
        "ana.blanco@ejemplo.com", settings.AXES_FAILURE_LIMIT, hace=settings.AXES_COOLOFF_TIME + timedelta(minutes=1)
    )

    assert fila_de(cliente_admin, "ana.blanco@ejemplo.com")["bloqueada"] is False


def test_un_intento_sin_usuario_no_bloquea_a_nadie(cliente_admin, equipo, axes_habilitado):
    intento_de_acceso(None, settings.AXES_FAILURE_LIMIT)

    assert not any(f["bloqueada"] for f in cliente_admin.get(URL).json()["results"])


def test_tras_cinco_logins_fallidos_reales_la_cuenta_aparece_bloqueada(cliente_admin, equipo, axes_habilitado):
    anonimo = APIClient()
    for _ in range(settings.AXES_FAILURE_LIMIT):
        anonimo.post(
            "/api/v1/auth/login/", {"email": "ana.blanco@ejemplo.com", "password": "incorrecta"}, format="json"
        )

    assert fila_de(cliente_admin, "ana.blanco@ejemplo.com")["bloqueada"] is True


# --- Rendimiento ---------------------------------------------------------------------


def test_el_numero_de_consultas_no_crece_con_los_usuarios(cliente_admin):
    UsuarioFactory(email="uno@ejemplo.com")
    with CaptureQueriesContext(connection) as pocas:
        cliente_admin.get(URL)

    for n in range(19):
        UsuarioFactory(email=f"extra{n:02d}@ejemplo.com")
    intento_de_acceso("extra00@ejemplo.com", settings.AXES_FAILURE_LIMIT)
    with CaptureQueriesContext(connection) as muchas:
        respuesta = cliente_admin.get(URL)

    assert len(respuesta.json()["results"]) == 20
    assert len(muchas) == len(pocas)


# --- Quién puede consultarla ---------------------------------------------------------


def test_sin_token_responde_401(api_client, llaves):
    respuesta = api_client.get(URL)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_un_no_administrador_recibe_403(api_client, llaves, rol):
    cliente_como(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.get(URL)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


def test_un_administrador_con_contrasena_temporal_recibe_403(api_client, admin):
    cliente_como(api_client, admin, debe_cambiar_password=True)

    respuesta = api_client.get(URL)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"
