"""HU-26 / ST-189: pruebas de GET /api/v1/auditoria/."""
from datetime import datetime, timezone as tz

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from comun.models import EventoAuditoria
from comun.roles import Rol
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auditoria/"
CAMPOS = {"id", "usuario", "accion", "resultado", "ip", "user_agent", "detalles", "fecha"}


def cliente_como(api_client, usuario):
    """Autentica con un token que lleva el claim `rol`, como el que emite usuarios/tokens.py."""
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api_client


@pytest.fixture(autouse=True)
def hash_rapido(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def admin(llaves):
    return UsuarioFactory(rol=Rol.ADMINISTRADOR)


@pytest.fixture
def cliente_admin(api_client, admin):
    return cliente_como(api_client, admin)


def evento(dia=None, **campos):
    """Crea un evento; `dia` (día de noviembre de 2026, 12:00 UTC) fija la fecha."""
    e = EventoAuditoria.objects.create(accion=campos.pop("accion", "login"), **campos)
    if dia:
        EventoAuditoria.objects.filter(pk=e.pk).update(fecha=datetime(2026, 11, dia, 12, tzinfo=tz.utc))
        e.refresh_from_db()
    return e


def ids(respuesta):
    return [fila["id"] for fila in respuesta.json()["results"]]


def test_administrador_ve_los_eventos_mas_recientes_primero(cliente_admin):
    for dia in (2, 3, 1):
        evento(dia)
    r = cliente_admin.get(URL)
    assert r.status_code == 200
    fechas = [f["fecha"] for f in r.json()["results"]]
    assert len(fechas) == 3 and fechas == sorted(fechas, reverse=True)
    assert set(r.json()["results"][0]) == CAMPOS


def test_pagina_de_20(cliente_admin):
    for _ in range(25):
        evento()
    r = cliente_admin.get(URL)
    assert r.json()["count"] == 25 and len(r.json()["results"]) == 20
    assert len(cliente_admin.get(URL, {"page": 2}).json()["results"]) == 5
    assert cliente_admin.get(URL, {"page": 9}).status_code == 404


def test_orden_estable_con_misma_fecha(cliente_admin):
    for _ in range(25):
        evento(5)
    todos = ids(cliente_admin.get(URL)) + ids(cliente_admin.get(URL, {"page": 2}))
    assert len(set(todos)) == 25


def test_filtra_por_accion(cliente_admin):
    evento(accion="login")
    evento(accion="logout")
    r = cliente_admin.get(URL, {"accion": "logout"})
    assert [f["accion"] for f in r.json()["results"]] == ["logout"]


def test_filtra_por_usuario(cliente_admin, admin):
    otra = UsuarioFactory()
    evento(usuario=admin)
    evento(usuario=otra)
    evento()
    r = cliente_admin.get(URL, {"usuario": str(otra.id)})
    assert [f["usuario"] for f in r.json()["results"]] == [str(otra.id)]


def test_filtra_por_rango_de_fechas(cliente_admin):
    for dia in (1, 2, 3, 4):
        evento(dia)
    r = cliente_admin.get(URL, {"desde": "2026-11-02", "hasta": "2026-11-03"})
    assert r.json()["count"] == 2


def test_filtros_combinados(cliente_admin, admin):
    evento(2, usuario=admin, accion="login")
    evento(2, usuario=admin, accion="logout")
    evento(9, usuario=admin, accion="login")
    evento(2, accion="login")
    r = cliente_admin.get(
        URL, {"accion": "login", "usuario": str(admin.id), "desde": "2026-11-01", "hasta": "2026-11-03"}
    )
    assert r.json()["count"] == 1


def test_desde_posterior_a_hasta_da_lista_vacia(cliente_admin):
    evento(2)
    r = cliente_admin.get(URL, {"desde": "2026-11-05", "hasta": "2026-11-01"})
    assert r.status_code == 200 and r.json()["results"] == []


@pytest.mark.parametrize("params", [{"usuario": "no-es-uuid"}, {"desde": "ayer"}, {"hasta": "2026-13-45"}])
def test_filtros_invalidos_dan_400(cliente_admin, params):
    r = cliente_admin.get(URL, params)
    assert r.status_code == 400 and r.json()["codigo"] == "datos_invalidos"


def test_sin_token_401(api_client):
    r = api_client.get(URL)
    assert r.status_code == 401 and r.json()["codigo"] == "no_autenticado"


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_cliente_y_operativo_reciben_403(api_client, llaves, rol):
    r = cliente_como(api_client, UsuarioFactory(rol=rol)).get(URL)
    assert r.status_code == 403 and r.json()["codigo"] == "sin_permiso"


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_no_se_puede_escribir(cliente_admin, metodo):
    evento()
    r = getattr(cliente_admin, metodo)(URL, {"accion": "x"}, format="json")
    assert r.status_code == 405 and r.json()["codigo"] == "metodo_no_permitido"
    assert EventoAuditoria.objects.count() == 1
