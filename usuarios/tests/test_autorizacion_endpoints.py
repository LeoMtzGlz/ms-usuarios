"""HU-13 / ST-129: matriz ejecutable de autorizaciÃ³n de los endpoints disponibles."""

import re

import pytest
from cryptography.fernet import Fernet
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from comun.roles import Rol
from usuarios.models import Estado
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


RUTAS_PUBLICAS = {
    ("get", "/api/v1/salud/"),
    ("post", "/api/v1/auth/registro/"),
    ("post", "/api/v1/auth/activar/"),
    ("post", "/api/v1/auth/login/"),
    ("post", "/api/v1/auth/token/renovar/"),
    ("get", "/api/v1/auth/privacidad/"),
    ("post", "/api/v1/auth/reenviar-codigo/"),
    ("post", "/api/v1/auth/recuperar/"),
    ("post", "/api/v1/auth/restablecer/"),
    ("get", "/api/schema/"),
    ("get", "/api/docs/"),
}

RUTAS_PROTEGIDAS = (
    ("post", "/api/v1/auth/2fa/activar/"),
    ("post", "/api/v1/auth/2fa/confirmar/"),
    ("post", "/api/v1/auth/2fa/desactivar/"),
    ("post", "/api/v1/auth/privacidad/aceptar/"),
    ("post", "/api/v1/auth/cambiar-password/"),
    ("post", "/api/v1/auth/logout-todo/"),
    ("get", "/api/v1/auth/perfil/"),
    ("patch", "/api/v1/auth/perfil/"),
    ("get", "/api/v1/auth/accesos/"),
    ("get", "/api/v1/auditoria/"),
    ("get", "/api/v1/usuarios/"),
    ("post", "/api/v1/usuarios/"),
    ("patch", "/api/v1/usuarios/<uuid>/"),
    ("post", "/api/v1/usuarios/<uuid>/desactivar/"),
    ("post", "/api/v1/usuarios/<uuid>/reactivar/"),
)


def _rutas(patterns=None, prefijo=""):
    """Recorre el Ã¡rbol real de URLconf y devuelve ruta y callback de cada vista."""
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


def _metodos_declarados(callback):
    """Obtiene los mÃ©todos que la vista implementa, sin contar OPTIONS ni HEAD implÃ­cito."""
    acciones = getattr(callback, "actions", None)
    if acciones:
        return {metodo.lower() for metodo in acciones}
    vista = getattr(callback, "cls", None)
    if vista is None:
        return set()
    return {
        metodo.lower()
        for metodo in getattr(vista, "http_method_names", ())
        if metodo.lower() not in {"head", "options"} and hasattr(vista, metodo.lower())
    }


def _normalizar_ruta(ruta):
    """Quita el nombre interno de los parÃ¡metros para compararlos con la matriz."""
    return re.sub(r"<uuid:[^>]+>", "<uuid>", ruta)


def _ruta_para_peticion(ruta):
    """Crea el usuario que necesitan las rutas con un UUID real."""
    if "<uuid>" not in ruta:
        return ruta
    usuario = UsuarioFactory()
    return ruta.replace("<uuid>", str(usuario.pk))


def _autenticar(api_client, usuario, **claims):
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    for nombre, valor in claims.items():
        acceso[nombre] = valor
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")


def test_toda_vista_publica_declara_allow_any_explicito():
    """Evita que una ruta pÃºblica dependa del permiso predeterminado de DRF."""
    rutas_publicas = {ruta for _metodo, ruta in RUTAS_PUBLICAS}
    callbacks = {ruta: callback for ruta, callback in _rutas() if ruta in rutas_publicas}

    assert callbacks.keys() == rutas_publicas
    faltantes = [
        ruta
        for ruta, callback in callbacks.items()
        if AllowAny not in (_permisos_declarados(callback) or ())
    ]
    assert faltantes == [], f"Rutas pÃºblicas sin AllowAny explÃ­cito: {faltantes}"


def test_todo_metodo_api_esta_en_la_matriz_de_autorizacion():
    """Falla cuando se agrega una ruta o mÃ©todo HTTP y se olvida clasificarlo."""
    rutas_reales = {
        (metodo, _normalizar_ruta(ruta))
        for ruta, callback in _rutas()
        if ruta.startswith("/api/")
        for metodo in _metodos_declarados(callback)
    }
    rutas_declaradas = RUTAS_PUBLICAS | set(RUTAS_PROTEGIDAS)

    assert rutas_reales == rutas_declaradas, (
        f"MÃ©todos sin clasificar: {sorted(rutas_reales - rutas_declaradas)}; "
        f"mÃ©todos inexistentes en la matriz: {sorted(rutas_declaradas - rutas_reales)}"
    )


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos", "esperado"),
    [
        ("get", "/api/v1/salud/", None, 200),
        ("post", "/api/v1/auth/registro/", {}, 400),
        ("post", "/api/v1/auth/activar/", {}, 400),
        ("post", "/api/v1/auth/login/", {}, 400),
        ("post", "/api/v1/auth/token/renovar/", {}, 400),
        ("get", "/api/v1/auth/privacidad/", None, 200),
        ("post", "/api/v1/auth/reenviar-codigo/", {}, 200),
        ("post", "/api/v1/auth/recuperar/", {}, 400),
        ("post", "/api/v1/auth/restablecer/", {}, 400),
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


def test_administrador_puede_listar_usuarios(api_client, llaves):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.get("/api/v1/usuarios/")

    assert respuesta.status_code == 200


def test_administrador_supera_autorizacion_antes_de_validar_el_alta(api_client, llaves):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.post("/api/v1/usuarios/", data={}, format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


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

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Nombre nuevo"
    objetivo.refresh_from_db()
    assert objetivo.first_name == "Nombre nuevo"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_usuario_no_administrador_no_consulta_auditoria(api_client, llaves, rol):
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.get("/api/v1/auditoria/")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


def test_administrador_supera_la_autorizacion_de_auditoria(api_client, llaves):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.get("/api/v1/auditoria/")

    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
@pytest.mark.parametrize("operacion", ["desactivar", "reactivar"])
def test_usuario_no_administrador_no_cambia_estado_de_cuentas(
    api_client, llaves, rol, operacion
):
    objetivo = UsuarioFactory()
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.post(
        f"/api/v1/usuarios/{objetivo.pk}/{operacion}/", {}, format="json"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


@pytest.mark.parametrize(
    ("operacion", "estado_inicial", "estado_esperado"),
    [
        ("desactivar", Estado.ACTIVO, Estado.INACTIVO),
        ("reactivar", Estado.INACTIVO, Estado.ACTIVO),
    ],
)
def test_administrador_supera_autorizacion_para_cambiar_estado(
    api_client, llaves, operacion, estado_inicial, estado_esperado
):
    objetivo = UsuarioFactory()
    if estado_inicial == Estado.INACTIVO:
        objetivo.cambiar_estado(Estado.INACTIVO)
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.post(
        f"/api/v1/usuarios/{objetivo.pk}/{operacion}/", {}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": str(objetivo.pk), "estado": estado_esperado}
    objetivo.refresh_from_db()
    assert objetivo.estado == estado_esperado


def test_administrador_no_puede_desactivar_su_2fa(api_client, llaves):
    _autenticar(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))

    respuesta = api_client.post("/api/v1/auth/2fa/desactivar/", {}, format="json")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "admin_requiere_2fa"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_cliente_y_operativo_superan_autorizacion_para_desactivar_2fa(
    api_client, llaves, rol
):
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.post("/api/v1/auth/2fa/desactivar/", {}, format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [ruta for ruta in RUTAS_PROTEGIDAS if ruta[1] != "/api/v1/auth/cambiar-password/"],
)
def test_contrasena_temporal_bloquea_rutas_protegidas(api_client, llaves, metodo, ruta):
    _autenticar(
        api_client,
        UsuarioFactory(rol=Rol.ADMINISTRADOR),
        debe_cambiar_password=True,
    )

    respuesta = getattr(api_client, metodo)(
        _ruta_para_peticion(ruta), data={}, format="json"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO, Rol.ADMINISTRADOR])
def test_cambiar_password_es_accesible_con_contrasena_temporal(api_client, llaves, rol):
    _autenticar(
        api_client,
        UsuarioFactory(rol=rol),
        debe_cambiar_password=True,
    )

    respuesta = api_client.post("/api/v1/auth/cambiar-password/", {}, format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO, Rol.ADMINISTRADOR])
@pytest.mark.parametrize(
    ("ruta", "datos", "esperado", "codigo"),
    [
        ("/api/v1/auth/2fa/activar/", {}, 200, None),
        (
            "/api/v1/auth/2fa/confirmar/",
            {"codigo": "000000"},
            400,
            "dos_factores_no_iniciado",
        ),
    ],
)
def test_todos_los_roles_superan_autorizacion_de_2fa(
    api_client, llaves, settings, rol, ruta, datos, esperado, codigo
):
    settings.CLAVE_CIFRADO_2FA = Fernet.generate_key().decode()
    _autenticar(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.post(ruta, datos, format="json")

    assert respuesta.status_code == esperado
    if codigo:
        assert respuesta.json()["codigo"] == codigo


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
