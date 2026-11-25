
"""HU-24 / ST-179: pruebas del límite de solicitudes al registro."""

import pytest
from django.core.cache.backends.locmem import LocMemCache
from rest_framework.throttling import ScopedRateThrottle


pytestmark = pytest.mark.django_db

URL_REGISTRO = "/api/v1/auth/registro/"


def test_sexta_solicitud_de_registro_responde_429(api_client, monkeypatch):
    """El registro permite cinco solicitudes por IP y bloquea la sexta."""

    # t-24/st-179: Aislar el contador para no afectar otras pruebas.
    cache_prueba = LocMemCache("throttle-registro-st-179", {})
    monkeypatch.setattr(ScopedRateThrottle, "cache", cache_prueba)

    ip_cliente = "198.51.100.179"

    for numero in range(1, 7):
        respuesta = api_client.post(
            URL_REGISTRO,
            data={},
            format="json",
            REMOTE_ADDR=ip_cliente,
            HTTP_X_FORWARDED_FOR=f"203.0.113.{numero}",
        )

        if numero <= 5:
            # Los datos vacíos fallan la validación, no el throttle.
            assert respuesta.status_code == 400
        else:
            assert respuesta.status_code == 429
            assert int(respuesta.headers["Retry-After"]) > 0
