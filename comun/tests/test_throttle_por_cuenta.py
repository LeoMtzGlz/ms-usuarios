"""hu-24/st-180: pruebas del throttle por cuenta.

Las pruebas de "límite + 1 devuelve 429" sobre los endpoints reales son de st-181.
"""
import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from comun.throttles import TASA_POR_DEFECTO, ThrottlePorCuenta, normalizar_identificador

factory = APIRequestFactory()


class VistaPrueba(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ThrottlePorCuenta]
    throttle_scope = "prueba"

    def post(self, request):
        return Response({"ok": True})


class OtraVista(VistaPrueba):
    throttle_scope = "otra"


@pytest.fixture
def cache_bd(db):
    """Crea la tabla de la caché en PostgreSQL (t-24/st-178) y la deja vacía."""
    call_command("createcachetable", verbosity=0)
    cache.clear()
    yield
    cache.clear()


def request_drf(datos):
    return Request(factory.post("/prueba/", datos, format="json"), parsers=[JSONParser()])


def clave(datos, vista=None):
    return ThrottlePorCuenta().get_cache_key(request_drf(datos), vista or VistaPrueba())


def enviar(datos, vista=VistaPrueba):
    return vista.as_view()(factory.post("/prueba/", datos, format="json"))


# --- Normalización del identificador ---

@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("  Ana@Mail.COM ", "ana@mail.com"),
        ("443 123 4567", "+524431234567"),
        ("+52 443 123 4567", "+524431234567"),
        ("12 34", "1234"),  # teléfono inválido: se cuenta igual
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_normalizar_identificador(valor, esperado):
    assert normalizar_identificador(valor) == esperado


# --- Clave de caché ---

def test_variaciones_del_mismo_correo_comparten_clave():
    assert clave({"correo": "ana@mail.com"}) == clave({"correo": "  ANA@mail.com"})


def test_variaciones_del_mismo_telefono_comparten_clave():
    assert clave({"telefono": "443 123 4567"}) == clave({"telefono": "+524431234567"})


def test_cuentas_distintas_tienen_claves_distintas():
    assert clave({"correo": "ana@mail.com"}) != clave({"correo": "luis@mail.com"})


def test_cada_endpoint_tiene_su_propio_contador():
    assert clave({"correo": "ana@mail.com"}) != clave({"correo": "ana@mail.com"}, OtraVista())


def test_la_clave_no_guarda_el_correo_en_claro():
    assert "ana" not in clave({"correo": "ana@mail.com"})


@pytest.mark.parametrize("campo", ["correo", "email", "telefono", "identificador"])
def test_acepta_los_campos_conocidos(campo):
    valor = "443 123 4567" if campo == "telefono" else "ana@mail.com"
    assert clave({campo: valor}) is not None


def test_sin_identificador_no_limita():
    assert clave({"otro": "dato"}) is None
    assert clave({}) is None


def test_usa_la_tasa_por_defecto():
    assert ThrottlePorCuenta().get_rate() == TASA_POR_DEFECTO == "3/hour"


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"cuenta": "5/minute"}})
def test_respeta_la_tasa_de_settings():
    assert ThrottlePorCuenta().get_rate() == "5/minute"


# --- Comportamiento con la caché en PostgreSQL ---

def test_cuenta_por_cuenta_y_no_por_ip(cache_bd):
    for _ in range(3):
        assert enviar({"correo": "ana@mail.com"}).status_code == 200
    # Misma IP, otra cuenta: no está limitada
    assert enviar({"correo": "luis@mail.com"}).status_code == 200
    # Misma cuenta escrita distinto: sí está limitada
    assert enviar({"correo": " ANA@mail.com"}).status_code == 429


def test_sin_identificador_nunca_responde_429(cache_bd):
    for _ in range(5):
        assert enviar({"otro": "dato"}).status_code == 200