import sys
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
    assert "datos_sensibles" in handlers["consola"]["filters"]
    assert "datos_sensibles_estricto" in handlers["archivo"]["filters"]


def test_el_archivo_oculta_codigos_sueltos_y_jwt_pero_la_consola_no():
    mensaje = (
        "Mensaje: tu código de activación es 483920 "
        "· refresh eyJhbGci.eyJzdWIi.Zmlyb2E"
    )
    registro = logging.LogRecord(
        "svc.notificaciones", logging.INFO, __file__, 1, mensaje, (), None
    )

    para_archivo = FiltrosDatosSensibles(estricto=True).filter(registro)

    assert isinstance(para_archivo, logging.LogRecord)
    assert "483920" not in para_archivo.getMessage()
    assert "eyJ" not in para_archivo.getMessage()
    assert "483920" in registro.getMessage()


def test_tambien_limpia_los_tracebacks():
    try:
        raise ValueError("password=Secreta123")
    except ValueError:

        registro = logging.LogRecord(
            "svc",
            logging.ERROR,
            __file__,
            1,
            "falló",
            (),
            sys.exc_info(),
        )

    FiltrosDatosSensibles().filter(registro)

    assert registro.exc_text is not None
    assert "Secreta123" not in registro.exc_text
