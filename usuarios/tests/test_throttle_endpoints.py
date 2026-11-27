"""HU-24 / ST-181: pruebas de "límite + 1 devuelve 429" sobre los endpoints reales.

Criterios de HU-24:
- login: 10 por minuto por IP.
- registro: 5 por hora por IP.
- recuperar y reenviar código: 3 por hora por IP y 3 por hora por cuenta.
- Al pasar el límite responde 429 con Retry-After.
- Los contadores se guardan en la caché de PostgreSQL (st-178), sin Redis.
"""
import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection

pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
URL_REGISTRO = "/api/v1/auth/registro/"
URL_RECUPERAR = "/api/v1/auth/recuperar/"
URL_REENVIAR = "/api/v1/auth/reenviar-codigo/"


@pytest.fixture(autouse=True)
def cache_bd(db):
    """Usa la caché real en PostgreSQL (st-178) y la deja vacía en cada prueba."""
    call_command("createcachetable", verbosity=0)
    cache.clear()
    yield
    cache.clear()


def enviar_n_veces(api_client, url, n, datos_por_intento, ip_por_intento):
    """Hace n POST y devuelve la lista de respuestas.

    datos_por_intento(i) e ip_por_intento(i) reciben el número de intento (1..n),
    así cada prueba decide si cambia la cuenta, la IP o ninguna.
    """
    respuestas = []
    for i in range(1, n + 1):
        respuestas.append(
            api_client.post(url, datos_por_intento(i), format="json", REMOTE_ADDR=ip_por_intento(i))
        )
    return respuestas


def assert_bloqueado(respuesta):
    assert respuesta.status_code == 429
    assert int(respuesta["Retry-After"]) > 0


def assert_no_bloqueado(respuestas):
    codigos = [r.status_code for r in respuestas]
    assert 429 not in codigos, f"Se bloqueó antes del límite: {codigos}"


# --- Límite por IP ---

@pytest.mark.parametrize(
    "url, limite, datos",
    [
        (URL_LOGIN, 10, lambda i: {"correo": f"nadie{i}@mail.com", "password": "x"}),
        (URL_REGISTRO, 5, lambda i: {}),
        (URL_RECUPERAR, 3, lambda i: {"identificador": f"nadie{i}@mail.com"}),
        (URL_REENVIAR, 3, lambda i: {"identificador": f"nadie{i}@mail.com"}),
    ],
    ids=["login", "registro", "recuperar", "reenviar"],
)
def test_limite_mas_uno_por_ip_responde_429(api_client, url, limite, datos):
    """Misma IP, cuenta distinta en cada intento: solo cuenta el límite por IP."""
    respuestas = enviar_n_veces(api_client, url, limite + 1, datos, lambda i: "198.51.100.10")

    assert_no_bloqueado(respuestas[:limite])
    assert_bloqueado(respuestas[limite])


def test_otra_ip_no_comparte_el_contador(api_client):
    """Agotar el límite desde una IP no bloquea a otra IP."""
    enviar_n_veces(
        api_client, URL_RECUPERAR, 4, lambda i: {"identificador": f"a{i}@mail.com"}, lambda i: "198.51.100.20"
    )

    respuesta = api_client.post(
        URL_RECUPERAR, {"identificador": "b@mail.com"}, format="json", REMOTE_ADDR="198.51.100.21"
    )
    assert respuesta.status_code == 200


# --- Límite por cuenta (ThrottlePorCuenta, st-180) ---

@pytest.mark.parametrize("url", [URL_RECUPERAR, URL_REENVIAR], ids=["recuperar", "reenviar"])
def test_limite_mas_uno_por_cuenta_responde_429(api_client, url):
    """Misma cuenta desde IPs distintas: cambiar de IP no da más intentos."""
    respuestas = enviar_n_veces(
        api_client, url, 4, lambda i: {"identificador": "ana@mail.com"}, lambda i: f"203.0.113.{i}"
    )

    assert_no_bloqueado(respuestas[:3])
    assert_bloqueado(respuestas[3])


def test_variaciones_del_correo_cuentan_como_la_misma_cuenta(api_client):
    """ANA@mail.com, ana@mail.com y ' Ana@Mail.com ' gastan el mismo contador."""
    variantes = ["ANA@mail.com", "ana@mail.com", " Ana@Mail.com ", "ana@MAIL.com"]
    respuestas = enviar_n_veces(
        api_client, URL_RECUPERAR, 4, lambda i: {"identificador": variantes[i - 1]}, lambda i: f"203.0.113.{i}"
    )

    assert_no_bloqueado(respuestas[:3])
    assert_bloqueado(respuestas[3])


def test_variaciones_del_telefono_cuentan_como_la_misma_cuenta(api_client):
    """443 123 4567 y +524431234567 son la misma cuenta (E.164)."""
    variantes = ["443 123 4567", "+524431234567", "4431234567", "+52 443 123 4567"]
    respuestas = enviar_n_veces(
        api_client, URL_RECUPERAR, 4, lambda i: {"identificador": variantes[i - 1]}, lambda i: f"203.0.113.{i}"
    )

    assert_no_bloqueado(respuestas[:3])
    assert_bloqueado(respuestas[3])


def test_el_contador_de_recuperar_no_gasta_el_de_reenviar(api_client):
    """Cada endpoint lleva su propio contador por cuenta."""
    enviar_n_veces(
        api_client, URL_RECUPERAR, 4, lambda i: {"identificador": "ana@mail.com"}, lambda i: f"203.0.113.{i}"
    )

    respuesta = api_client.post(
        URL_REENVIAR, {"identificador": "ana@mail.com"}, format="json", REMOTE_ADDR="203.0.113.50"
    )
    assert respuesta.status_code == 200


# --- Dónde se guardan los contadores ---

def test_los_contadores_se_guardan_en_la_cache_de_postgresql(api_client):
    api_client.post(URL_RECUPERAR, {"identificador": "ana@mail.com"}, format="json", REMOTE_ADDR="198.51.100.30")

    with connection.cursor() as cursor:
        cursor.execute("SELECT cache_key FROM cache_table")
        claves = [fila[0] for fila in cursor.fetchall()]

    assert any("recuperar" in clave for clave in claves), claves
    # La clave por cuenta lleva un hash, nunca el correo en claro.
    assert not any("ana@mail.com" in clave for clave in claves)
