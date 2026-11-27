"""Formato único de errores: {"codigo", "mensaje", "campos"}.

Toda respuesta de error de la API pasa por `manejador_errores`, configurado en
REST_FRAMEWORK["EXCEPTION_HANDLER"]. Nunca se devuelve un stacktrace.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from rest_framework import exceptions, status
from rest_framework.views import exception_handler

logger = logging.getLogger("svc.errores")


# --- Catálogo de errores de negocio (ver docs/catalogo-errores.md) ---------------

class CredencialesInvalidas(exceptions.AuthenticationFailed):
    default_detail = "Correo, teléfono o contraseña incorrectos."
    default_code = "credenciales_invalidas"


class TokenInvalido(exceptions.AuthenticationFailed):
    default_detail = "La sesión no es válida o ya venció. Inicia sesión de nuevo."
    default_code = "token_invalido"


class CuentaPendiente(exceptions.PermissionDenied):
    default_detail = "Tu cuenta aún no está activa. Escribe el código que te enviamos."
    default_code = "cuenta_pendiente"


class CuentaInactiva(exceptions.PermissionDenied):
    default_detail = "Tu cuenta está desactivada. Contacta al administrador."
    default_code = "cuenta_inactiva"


class CuentaBloqueada(exceptions.PermissionDenied):
    default_detail = "Demasiados intentos fallidos. Tu cuenta está bloqueada 15 minutos."
    default_code = "cuenta_bloqueada"


class DebeCambiarPassword(exceptions.PermissionDenied):
    default_detail = "Debes cambiar tu contraseña temporal antes de continuar."
    default_code = "debe_cambiar_password"

<<<<<<< HEAD
# t-33/st-219: login con Google
class TokenGoogleInvalido(exceptions.AuthenticationFailed):
    default_detail = "No se pudo verificar tu cuenta de Google. Intenta de nuevo."
    default_code = "token_google_invalido"


class GoogleNoConfigurado(exceptions.APIException):
    status_code = 503
    default_detail = "El inicio de sesión con Google no está disponible."
    default_code = "google_no_configurado"

=======
class UnicoAdministrador(exceptions.PermissionDenied):
    default_detail = "Eres el único administrador activo. Nombra a otro antes de eliminar tu cuenta."
    default_code = "unico_administrador"
>>>>>>> 1f11747d4f8e271dd947680c7f79e9ca34dfd2c2
    
class CodigoInvalido(exceptions.ValidationError):
    default_detail = "El código es incorrecto."
    default_code = "codigo_invalido"


class CodigoExpirado(exceptions.ValidationError):
    default_detail = "El código ya venció o ya se usó. Pide uno nuevo."
    default_code = "codigo_expirado"

#t-30/st-206
class DosFactoresYaActivo(exceptions.ValidationError):
    default_detail = "La verificación en dos pasos ya está activa en tu cuenta."
    default_code = "dos_factores_ya_activo"


class DosFactoresNoIniciado(exceptions.ValidationError):
    default_detail = "Primero solicita la activación de la verificación en dos pasos."
    default_code = "dos_factores_no_iniciado"

# Códigos genéricos por tipo de excepción de DRF
CODIGOS_POR_TIPO = [
    (exceptions.ValidationError, "datos_invalidos"),
    (exceptions.NotAuthenticated, "no_autenticado"),
    (exceptions.AuthenticationFailed, "token_invalido"),
    (exceptions.PermissionDenied, "sin_permiso"),
    (exceptions.NotFound, "no_encontrado"),
    (exceptions.MethodNotAllowed, "metodo_no_permitido"),
    (exceptions.Throttled, "demasiados_intentos"),
    (exceptions.ParseError, "datos_invalidos"),
]
CODIGOS_GENERICOS_DRF = {
    "invalid", "required", "not_authenticated", "authentication_failed", "permission_denied",
    "not_found", "method_not_allowed", "throttled", "parse_error", "token_not_valid", "user_inactive",
    "user_not_found", "no_active_account", "error",
}
MENSAJES = {
    "datos_invalidos": "Revisa los datos enviados.",
    "no_autenticado": "Necesitas iniciar sesión.",
    "token_invalido": TokenInvalido.default_detail,
    "sin_permiso": "No tienes permiso para esta acción.",
    "no_encontrado": "No encontramos lo que buscas.",
    "metodo_no_permitido": "Método no permitido.",
    "demasiados_intentos": "Demasiadas solicitudes. Intenta más tarde.",
    "error_interno": "Ocurrió un error inesperado. Intenta más tarde.",
}


def manejador_errores(exc, context):
    respuesta = exception_handler(exc, context)  # convierte Http404 y PermissionDenied de Django
    if respuesta is None:
        if settings.DEBUG:
            return None  # en desarrollo se ve el error completo de Django
        logger.exception("Error no controlado en %s", context.get("view"))
        return JsonResponse(
            {"codigo": "error_interno", "mensaje": MENSAJES["error_interno"], "campos": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.APIException):
        codigo = _codigo_propio(exc) or next(
            (c for tipo, c in CODIGOS_POR_TIPO if isinstance(exc, tipo)), "error"
        )
    else:  # Http404 o PermissionDenied de Django
        codigo = "no_encontrado" if respuesta.status_code == 404 else "sin_permiso"

    campos = {}
    if isinstance(respuesta.data, dict) and "detail" not in respuesta.data:
        campos = {k: [str(m) for m in v] if isinstance(v, list) else [str(v)] for k, v in respuesta.data.items()}
        campos.pop("non_field_errors", None)
    if codigo in MENSAJES and (codigo != "datos_invalidos" or campos):
        mensaje = MENSAJES[codigo]
    else:
        mensaje = _primer_mensaje(respuesta.data)
    if isinstance(exc, exceptions.Throttled) and exc.wait:
        mensaje = f"Demasiadas solicitudes. Intenta de nuevo en {int(exc.wait)} segundos."

    respuesta.data = {"codigo": codigo, "mensaje": mensaje, "campos": campos}
    return respuesta


def no_encontrado(request, exception=None):
    """handler404 para rutas que no existen (con DEBUG=False)."""
    return JsonResponse(
        {"codigo": "no_encontrado", "mensaje": MENSAJES["no_encontrado"], "campos": {}}, status=404
    )


def error_interno(request):
    """handler500: nunca un stacktrace."""
    return JsonResponse(
        {"codigo": "error_interno", "mensaje": MENSAJES["error_interno"], "campos": {}}, status=500
    )


def _codigo_propio(exc):
    codigos = exc.get_codes()
    if isinstance(codigos, str) and codigos not in CODIGOS_GENERICOS_DRF:
        return codigos
    if isinstance(codigos, list) and len(codigos) == 1 and codigos[0] not in CODIGOS_GENERICOS_DRF:
        return codigos[0]
    return None


def _primer_mensaje(detalle):
    if isinstance(detalle, list) and detalle:
        return _primer_mensaje(detalle[0])
    if isinstance(detalle, dict) and detalle:
        return _primer_mensaje(next(iter(detalle.values())))
    return str(detalle)


# hu-25/st-184: handler propio para el bloqueo de django-axes
def respuesta_bloqueo_axes(request, response, credentials, *args, **kwargs):
    """Devuelve el bloqueo de django-axes con el formato estándar de la API."""
    exc = CuentaBloqueada()
    return JsonResponse(
        {
            "codigo": exc.default_code,
            "mensaje": str(exc.detail),
            "campos": {},
        },
        status=status.HTTP_403_FORBIDDEN,
    )

def marcar_bloqueo_en_request_django(sender, request, **kwargs):
    """Copia la marca de bloqueo de DRF al HttpRequest original."""
    original = getattr(request, "_request", None)
    if original is not None:
        original.axes_locked_out = True
        original.axes_credentials = getattr(request, "axes_credentials", None)


# t-32/st-215: desactivar 2FA
class DosFactoresNoActivo(exceptions.ValidationError):
    default_detail = "La verificación en dos pasos no está activa en tu cuenta."
    default_code = "dos_factores_no_activo"


class AdminRequiere2FA(exceptions.PermissionDenied):
    default_detail = "Los administradores no pueden desactivar la verificación en dos pasos."
    default_code = "admin_requiere_2fa"
