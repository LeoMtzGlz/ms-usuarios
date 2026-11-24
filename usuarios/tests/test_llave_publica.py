"""T-14/ST-135: pruebas del endpoint público de la llave RS256."""

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.core.cache import cache

URL = "/api/v1/auth/llave-publica/"


def _entero_base64url(valor):
    relleno = "=" * (-len(valor) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(valor + relleno), "big")


@pytest.fixture(autouse=True)
def limpiar_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "st-135",
        }
    }
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def llave_configurada(llaves, monkeypatch):
    _, publica = llaves
    monkeypatch.setitem(settings.SIMPLE_JWT, "VERIFYING_KEY", publica)
    return publica


def test_es_publico_y_entrega_una_jwks(api_client, llave_configurada):
    respuesta = api_client.get(URL)

    assert respuesta.status_code == 200
    assert len(respuesta.json()["keys"]) == 1
    assert respuesta.json()["keys"][0].keys() == {"kty", "use", "alg", "kid", "n", "e"}


def test_la_jwk_corresponde_a_la_llave_publica_configurada(api_client, llave_configurada):
    esperados = serialization.load_pem_public_key(llave_configurada.encode()).public_numbers()

    jwk = api_client.get(URL).json()["keys"][0]

    assert jwk["kty"] == "RSA"
    assert jwk["use"] == "sig"
    assert jwk["alg"] == "RS256"
    assert _entero_base64url(jwk["n"]) == esperados.n
    assert _entero_base64url(jwk["e"]) == esperados.e


def test_nunca_expone_material_privado(api_client, llave_configurada):
    respuesta = api_client.get(URL)
    cuerpo = respuesta.json()

    assert not ({"d", "p", "q", "dp", "dq", "qi"} & cuerpo["keys"][0].keys())
    assert "PRIVATE KEY" not in respuesta.content.decode()


def test_ignora_un_encabezado_de_autorizacion_invalido(api_client, llave_configurada):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer esto-no-es-un-token")

    assert api_client.get(URL).status_code == 200


def test_se_puede_cachear_publicamente_durante_una_hora(api_client, llave_configurada):
    respuesta = api_client.get(URL)

    directivas = {parte.strip() for parte in respuesta["Cache-Control"].split(",")}
    assert "public" in directivas
    assert "max-age=3600" in directivas


def test_la_respuesta_cacheada_es_estable(api_client, llave_configurada, monkeypatch):
    primera = api_client.get(URL).json()
    monkeypatch.setitem(settings.SIMPLE_JWT, "VERIFYING_KEY", "no-es-una-llave")

    segunda = api_client.get(URL).json()

    assert segunda == primera


@pytest.mark.parametrize("valor", ["", "no-es-una-llave"])
def test_configuracion_ausente_o_invalida_responde_503(api_client, monkeypatch, valor):
    monkeypatch.setitem(settings.SIMPLE_JWT, "VERIFYING_KEY", valor)

    respuesta = api_client.get(URL)

    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "codigo": "llave_publica_no_configurada",
        "mensaje": "La llave pública no está disponible.",
        "campos": {},
    }
