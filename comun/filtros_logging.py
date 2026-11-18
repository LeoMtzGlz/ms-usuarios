"""
Filtros de seguridad para los registros de la aplicación
"""

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


class FiltrosDatosSensibles(logging.Filter):
    """
    Oculta contraseñas, códigos y tokens antes de escribir un log.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        mensaje = record.getMessage()

        def reemplazar_dato(match: re.Match) -> str:
            prefijo = match.group("prefijo")
            comilla = match.group("comilla")

            if comilla:
                return f"{prefijo}{comilla}***{comilla}"

            return f"{prefijo}***"

        mensaje = _PATRON_DATOS_SENSIBLES.sub(reemplazar_dato, mensaje)
        mensaje = _PATRON_BEARER.sub("Bearer ***", mensaje)

        # Evita que logging vuelva a interpolar los argumentos originales.
        record.msg = mensaje
        record.args = ()

        return True
