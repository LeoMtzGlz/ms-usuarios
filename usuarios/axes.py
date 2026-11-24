"""Funciones auxiliares para la identificación de intentos fallidos en django-axes."""

from django.core.exceptions import ValidationError

from usuarios.telefono import normalizar_telefono


def normalizar_identificador(identificador):
    """Normaliza correos y teléfonos para agrupar los intentos de autenticación."""
    if identificador is None:
        return None

    identificador = str(identificador).strip()
    if not identificador:
        return None

    if "@" in identificador:
        return identificador.lower()

    try:
        return normalizar_telefono(identificador)
    except ValidationError:
        return identificador.lower()


def obtener_usuario_axes(request, credentials):
    """Obtiene el identificador normalizado usado en el intento de autenticación."""
    identificador = None

    if credentials:
        identificador = credentials.get("username") or credentials.get("email")

    if not identificador:
        datos = getattr(request, "data", None)
        if datos is None:
            datos = getattr(request, "POST", {})

        identificador = datos.get("email") or datos.get("username")

    return normalizar_identificador(identificador)
