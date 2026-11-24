"""Funciones auxiliares para la identificación de intentos fallidos en django-axes."""


def obtener_usuario_axes(request, credentials):
    """Obtiene el identificador usado en el intento de autenticación."""
    if credentials:
        identificador = credentials.get("username") or credentials.get("email")
        if identificador:
            return str(identificador)

    datos = getattr(request, "data", None)
    if datos is None:
        datos = getattr(request, "POST", {})

    return datos.get("email") or datos.get("username")
