
"""Filtros de seguridad para los registros de la aplicación."""

import copy
import logging
import re


_PATRON_DATOS_SENSIBLES = re.compile(
    r"""(?P<prefijo>["']?(?:password|passwd|contrasena|contraseña|code|codigo|código|otp|token|access|refresh|secret|secreto)["']?\s*[:=]\s*)"""
    r"""(?:(?P<comilla>["'])(?P<valor_comillado>.*?)(?P=comilla)|(?P<valor_simple>[^\s,;}\]]+))""",
    re.IGNORECASE,
)

_PATRON_BEARER = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)

# Solo en modo estricto: JWT sueltos y códigos de seis dígitos.
_PATRON_JWT = re.compile(
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)

_PATRON_CODIGO = re.compile(r"(?<![\w+-])\d{6}(?![\w-])")


def _reemplazar_dato(match: re.Match) -> str:
    prefijo = match.group("prefijo")
    comilla = match.group("comilla")

    if comilla:
        return f"{prefijo}{comilla}***{comilla}"

    return f"{prefijo}***"


class FiltrosDatosSensibles(logging.Filter):
    """Oculta datos sensibles en los registros de la aplicación.

    Con estricto=True, también oculta cualquier JWT y código de seis dígitos.
    """

    def __init__(self, name: str = "", estricto: bool = False):
        super().__init__(name)
        self.estricto = estricto

    def ocultar(self, texto: str) -> str:
        texto = _PATRON_DATOS_SENSIBLES.sub(_reemplazar_dato, texto)
        texto = _PATRON_BEARER.sub("Bearer ***", texto)

        if self.estricto:
            texto = _PATRON_JWT.sub("***", texto)
            texto = _PATRON_CODIGO.sub("******", texto)

        return texto

    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        # El modo estricto trabaja sobre una copia para no modificar
        # el registro original que recibe también la consola.
        registro = copy.copy(record) if self.estricto else record

        registro.msg = self.ocultar(record.getMessage())
        registro.args = ()

        # Convierte y limpia el traceback antes de escribirlo.
        if record.exc_info and not record.exc_text:
            registro.exc_text = logging.Formatter().formatException(
                record.exc_info
            )

        if registro.exc_text:
            registro.exc_text = self.ocultar(registro.exc_text)

        return registro if self.estricto else True
