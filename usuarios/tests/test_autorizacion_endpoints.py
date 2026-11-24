"""HU-13 / ST-129: matriz ejecutable de autorización de los endpoints disponibles."""

import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from comun.roles import Rol
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


RUTAS_PUBLICAS = {
    "/api/v1/salud/",
    "/api/v1/auth/registro/",
    "/api/v1/auth/login/",
    "/api/v1/auth/privacidad/",
    "/api/schema/",
    "/api/docs/",
}

RUTAS_PROTEGIDAS = (
    ("post", "/api/v1/auth/2fa/activar/"),
    ("post", "/api/v1/auth/2fa/confirmar/"),
    ("post", "/api/v1/auth/privacidad/aceptar/"),
    ("post", "/api/v1/auth/cambiar-password/"),
    ("get", "/api/v1/usuarios/"),
    ("post", "/api/v1/usuarios/"),
    ("patch", "/api/v1/usuarios/<uuid>/"),
)


def _rutas(patterns=None, prefijo=""):
    """Recorre el árbol real de URLconf y devuelve ruta y callback de cada vista."""
    patterns = get_resolver().url_patterns if patterns is None else patterns
    for pattern in patterns:
        ruta = f"{prefijo}{pattern.pattern}"
        if isinstance(pattern, URLResolver):
            yield from _rutas(pattern.url_patterns, ruta)
        elif isinstance(pattern, URLPattern):
            yield f"/{ruta}", pattern.callback


def _permisos_declarados(callback):
    """Lee solo declaraciones locales, no permisos heredados accidentalmente."""
    iniciales = getattr(callback, "initkwargs", {})
    if "permission_classes" in iniciales:
        return iniciales["permission_classes"]
    vista = getattr(callback, "cls", None)
    return None if vista is None else vista.__dict__.get("permission_classes")


def _normalizar_ruta(ruta):
    """Quita el nombre interno de los parámetros para compararlos con la matriz."""
    return re.sub(r"<uuid:[^>]+>", "<uuid>", ruta)


def _ruta_para_peticion(ruta):
    """Crea el usuario que necesitan las rutas con un UUID real."""
    if "<uuid>" not in ruta:
        return ruta
    usuario = UsuarioFactory()
    return ruta.replace("<uuid>", str(usuario.pk))


def _autenticar(api_client, usuario):
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")


def test_toda_vista_publica_declara_allow_any_explicito():
    """Evita que una ruta pública dependa del permiso predeterminado de DRF."""
    callbacks = {ruta: callback for ruta, callback in _rutas() if ruta in RUTAS_PUBLICAS}

    assert callbacks.keys() == RUTAS_PUBLICAS
    faltantes = [
        ruta
        for ruta, callback in callbacks.items()
        if AllowAny not in (_permisos_declarados(callback) or ())
    ]
    assert faltantes == [], f"Rutas públicas sin AllowAny explícito: {faltantes}"


def test_toda_ruta_api_esta_en_la_matriz_de_autorizacion():
    """Falla cuando se agrega un endpoint y se olvida definir su autorización."""
    rutas_reales = {
        _normalizar_ruta(ruta)
        for ruta, _callback in _rutas()
        if ruta.startswith("/api/")
    }
    rutas_declaradas = RUTAS_PUBLICAS | {ruta for _metodo, ruta in RUTAS_PROTEGIDAS}

    assert rutas_reales == rutas_declaradas, (
        f"Rutas sin clasificar: {sorted(rutas_reales - rutas_declaradas)}; "
        f"rutas inexistentes en la matriz: {sorted(rutas_declaradas - rutas_reales)}"
    )


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos", "esperado"),
    [
        ("get", "/api/v1/salud/", None, 200),
        ("post", "/api/v1/auth/registro/", {}, 400),
        ("post", "/api/v1/auth/login/", {}, 400),
        ("get", "/api/v1/auth/privacidad/", None, 200),
        ("get", "/api/schema/", None, 200),
        ("get", "/api/docs/", None, 200),
    ],
)
def test_rutas_publicas_no_exigen_token(api_client, metodo, ruta, datos, esperado):
    respuesta = getattr(api_client, metodo)(ruta, data=datos, format="json")

    assert respuesta.status_code == esperado
    assert respuesta.status_code not in (401, 403)


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_PROTEGIDAS)
def test_rutas_protegidas_rechazan_peticion_sin_token(api_client, llaves, metodo, ruta):
    respuesta = getattr(api_client, metodo)(
        _ruta_para_peticion(ruta), data={}, format="json"
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
@pytest.mark.parametrize("metodo", ["get", "post"])
def test_usuario_no_administrador_no_accede_a_usuarios(api_client, llaves, rol, metodo):
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = getattr(api_client, metodo)("/api/v1/usuarios/", data={}, format="json")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


@pytest.mark.parametrize("metodo", ["get", "post"])
def test_administrador_supera_la_autorizacion_de_usuarios(api_client, llaves, metodo):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = getattr(api_client, metodo)("/api/v1/usuarios/", data={}, format="json")

    assert respuesta.status_code not in (401, 403)


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_usuario_no_administrador_no_edita_usuarios(api_client, llaves, rol):
    objetivo = UsuarioFactory()
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.patch(
        f"/api/v1/usuarios/{objetivo.pk}/", {"nombre": "Nombre nuevo"}, format="json"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


def test_administrador_supera_la_autorizacion_para_editar(api_client, llaves):
    objetivo = UsuarioFactory()
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.patch(
        f"/api/v1/usuarios/{objetivo.pk}/", {"nombre": "Nombre nuevo"}, format="json"
    )

    assert respuesta.status_code not in (401, 403)


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO, Rol.ADMINISTRADOR])
def test_todo_usuario_autenticado_puede_aceptar_privacidad(api_client, llaves, rol):
    usuario = UsuarioFactory(rol=rol)
    _autenticar(api_client, usuario)

    respuesta = api_client.post("/api/v1/auth/privacidad/aceptar/", {}, format="json")

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.acepto_privacidad_en is not None


def test_admin_de_django_no_se_habilita_con_un_rol_de_la_api(api_client, llaves):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR, is_staff=False))

    respuesta = api_client.get("/admin/")

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/admin/login/")
