import logging

import pytest
from django.conf import settings

from comun.filtros_logging import FiltrosDatosSensibles


@pytest.mark.parametrize(
    ("mensaje", "dato_sensible"),
    [
        ("password=Secreta123", "Secreta123"),
        ("contrasena: MiClave123", "MiClave123"),
        ("contraseña: MiClave123", "MiClave123"),  # Nuevo
        ("codigo=123456", "123456"),
        ("código=123456", "123456"),  # Nuevo
        ("token=abc123xyz", "abc123xyz"),
        ("Bearer eyJhbGciOiJIUzI1NiJ9", "eyJhbGciOiJIUzI1NiJ9"),
    ],
)
def test_filtro_oculta_datos_sensibles(mensaje, dato_sensible):
    filtro = FiltrosDatosSensibles()
    registro = logging.LogRecord(
        "svc.seguridad", logging.INFO, __file__, 1, mensaje, (), None
    )

    resultado = filtro.filter(registro)

    assert resultado is True
    assert dato_sensible not in registro.getMessage()
    assert "***" in registro.getMessage()


def test_filtro_conserva_mensajes_sin_datos_sensibles():
    filtro = FiltrosDatosSensibles()
    mensaje = "Inicio de sesión correcto"
    registro = logging.LogRecord(
        "svc.seguridad", logging.INFO, __file__, 1, mensaje, (), None
    )

    filtro.filter(registro)

    assert registro.getMessage() == mensaje


def test_filtro_oculta_datos_en_mensajes_con_argumentos():
    filtro = FiltrosDatosSensibles()
    registro = logging.LogRecord(
        "svc.seguridad",
        logging.INFO,
        __file__,
        1,
        "password=%s",
        ("Secreta123",),
        None,
    )

    filtro.filter(registro)

    assert "Secreta123" not in registro.getMessage()
    assert "***" in registro.getMessage()
    assert registro.args == ()


def test_handlers_de_logging_aplican_el_filtro():
    handlers = settings.LOGGING["handlers"]

    assert {"consola", "archivo"} <= set(handlers)

    for nombre in ("consola", "archivo"):
        assert "datos_sensibles" in handlers[nombre]["filters"]
