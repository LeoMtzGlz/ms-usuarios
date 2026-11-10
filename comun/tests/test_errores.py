import pytest

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
