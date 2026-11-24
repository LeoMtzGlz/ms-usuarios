"""hu-24/st-180: throttle por cuenta.

Los throttles de DRF por IP (ScopedRateThrottle, t-24/st-179) no frenan a quien cambia de IP
para pedir códigos a la misma cuenta. Este throttle usa como clave el correo o teléfono que
llega en el body, así cada cuenta tiene su propio contador sin importar desde dónde llegue.

Uso en una vista (recuperar contraseña, reenviar código):

    from comun.throttles import ThrottlePorCuenta

    class ReenviarCodigoView(APIView):
        throttle_scope = "reenviar_codigo"          # el de st-179, para el límite por IP
        throttle_classes = [ScopedRateThrottle, ThrottlePorCuenta]

- Límite: 3 por hora, o el valor de DEFAULT_THROTTLE_RATES["cuenta"] si alguien lo define.
- Cada endpoint lleva su propio contador (se separa por ``throttle_scope`` de la vista).
- Los contadores se guardan en la caché de PostgreSQL (t-24/st-178).
- Al pasar el límite DRF lanza Throttled: 429 con Retry-After y el formato estándar de errores.
"""
import hashlib

from django.core.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle

from usuarios.telefono import normalizar_telefono

TASA_POR_DEFECTO = "3/hour"

# Campos del body donde puede venir la cuenta, en orden de preferencia.
CAMPOS_IDENTIFICADOR = ("correo", "email", "telefono", "identificador")


def normalizar_identificador(valor) -> str | None:
    """Deja el identificador igual que en el modelo para que las variaciones no esquiven el límite.

    - Correo: sin espacios y en minúsculas ("  Ana@Mail.com " -> "ana@mail.com").
    - Teléfono: E.164 ("443 123 4567" -> "+524431234567").
    - Un teléfono inválido se cuenta tal cual (sin espacios): también gasta intentos.
    """
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if not texto:
        return None
    if "@" in texto:
        return texto.lower()
    try:
        return normalizar_telefono(texto)
    except ValidationError:
        return "".join(texto.split()).lower()


class ThrottlePorCuenta(SimpleRateThrottle):
    """Limita las solicitudes por cuenta (correo o teléfono del body), no por IP."""

    scope = "cuenta"

    def get_rate(self):
        # api_settings se lee en cada llamada para respetar override_settings en las pruebas.
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope) or TASA_POR_DEFECTO

    def get_cache_key(self, request, view):
        identificador = self.obtener_identificador(request)
        if identificador is None:
            return None  # sin cuenta en el body no hay nada que limitar aquí (queda el límite por IP)
        # Se guarda un hash para no dejar correos ni teléfonos en la tabla de caché.
        huella = hashlib.sha256(identificador.encode()).hexdigest()
        vista = getattr(view, "throttle_scope", None) or view.__class__.__name__
        return f"throttle_{self.scope}_{vista}_{huella}"

    def obtener_identificador(self, request) -> str | None:
        datos = getattr(request, "data", None)
        if not hasattr(datos, "get"):
            return None
        for campo in CAMPOS_IDENTIFICADOR:
            identificador = normalizar_identificador(datos.get(campo))
            if identificador:
                return identificador
        return None