import pytest
import json
from django.test import RequestFactory
from comun.errores import respuesta_bloqueo_axes

pytestmark = [pytest.mark.django_db, pytest.mark.urls("comun.tests.urls_errores")]


def test_error_de_validacion_indica_los_campos(client):
    r = client.post("/validacion/", {"correo": "no-es-correo", "edad": -1}, content_type="application/json")
    assert r.status_code == 400
    cuerpo = r.json()
    assert cuerpo["codigo"] == "datos_invalidos"
    assert set(cuerpo["campos"]) == {"correo", "edad"}
    assert isinstance(cuerpo["campos"]["correo"], list)


@pytest.mark.parametrize(
    ("cual", "estado", "codigo"),
    [
        ("credenciales", 401, "credenciales_invalidas"),
        ("pendiente", 403, "cuenta_pendiente"),
        ("codigo", 400, "codigo_expirado"),
        ("throttle", 429, "demasiados_intentos"),
    ],
)
def test_errores_de_negocio_usan_su_codigo(client, cual, estado, codigo):
    r = client.get(f"/lanza/{cual}/")
    assert r.status_code == estado
    assert r.json()["codigo"] == codigo
    assert set(r.json()) == {"codigo", "mensaje", "campos"}


def test_throttle_dice_cuanto_esperar(client):
    r = client.get("/lanza/throttle/")
    assert r["Retry-After"] == "42"
    assert "42 segundos" in r.json()["mensaje"]


def test_error_inesperado_no_muestra_stacktrace(client, settings):
    settings.DEBUG = False
    r = client.get("/lanza/explota/")
    assert r.status_code == 500
    assert r.json()["codigo"] == "error_interno"
    assert "detalle interno" not in r.content.decode()


@pytest.mark.urls("config.urls")
def test_ruta_inexistente_responde_404_con_el_formato(client):
    r = client.get("/api/v1/no-existe/")
    assert r.status_code == 404
    assert r.json()["codigo"] == "no_encontrado"


# hu-25/st-184: verifica el formato estándar de respuesta del bloqueo
def test_bloqueo_axes_usa_formato_estandar():
    request = RequestFactory().post("/api/v1/auth/login/")
    respuesta = respuesta_bloqueo_axes(request, None, {"username": "usuario"})

    assert respuesta.status_code == 403
    assert json.loads(respuesta.content) == {
        "codigo": "cuenta_bloqueada",
        "mensaje": "Demasiados intentos fallidos. Tu cuenta está bloqueada 15 minutos.",
        "campos": {},
    }

# hu-25/st-184: el bloqueo por DRF responde con el formato estándar
def test_bloqueo_por_drf_responde_403_estandar(client):
    from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

    usuario = UsuarioFactory()

    for _ in range(4):
        respuesta = client.post(
            "/login/",
            {"email": usuario.email, "password": "mala"},
        )
        assert respuesta.status_code == 401

    quinto = client.post(
        "/login/",
        {"email": usuario.email, "password": "mala"},
    )
    correcta = client.post(
        "/login/",
        {"email": usuario.email, "password": PASSWORD_PRUEBA},
    )

    for respuesta in (quinto, correcta):
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "cuenta_bloqueada"
        assert set(respuesta.json()) == {"codigo", "mensaje", "campos"}
