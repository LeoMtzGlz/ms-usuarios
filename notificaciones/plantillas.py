import re
from django.template.loader import render_to_string
from django.utils.html import strip_tags

PLANTILLAS_CORREO = {
    "activacion": {
        "template": "notificaciones/correo/activacion.html",
        "asunto_default": "Activa tu cuenta",
    },
    "bienvenida": {
        "template": "notificaciones/correo/bienvenida.html",
        "asunto_default": "¡Bienvenido a la plataforma!",
    },
    "recuperacion_password": {
        "template": "notificaciones/correo/recuperacion_password.html",
        "asunto_default": "Recuperación de contraseña",
    },
    "cambio_password": {
        "template": "notificaciones/correo/cambio_password.html",
        "asunto_default": "Tu contraseña ha sido actualizada",
    },
    "bloqueo_cuenta": {
        "template": "notificaciones/correo/bloqueo_cuenta.html",
        "asunto_default": "Aviso de seguridad: Cuenta bloqueada",
    },
    # t-15/st-142: aviso al operativo al que un administrador le crea la cuenta (HU-15)
    "cuenta_creada": {
        "template": "notificaciones/correo/cuenta_creada.html",
        "asunto_default": "Tu cuenta ha sido creada",
    },
}

# Alias de compatibilidad con llamadas existentes en el proyecto (ej. test_services.py)
ALIAS_PLANTILLAS = {
    "codigo_activacion": "activacion",
}


def renderizar_plantilla_correo(nombre_plantilla: str, contexto: dict | None = None) -> tuple[str, str, str]:
    """
    Renderiza una de las plantillas de correo de PLANTILLAS_CORREO.
    Retorna: (asunto, texto_plano, html)
    """
    clave = ALIAS_PLANTILLAS.get(nombre_plantilla, nombre_plantilla)

    if clave not in PLANTILLAS_CORREO:
        raise ValueError(f"Plantilla de correo desconocida: '{nombre_plantilla}'")

    config = PLANTILLAS_CORREO[clave]
    ctx = contexto or {}

    html = render_to_string(config["template"], ctx)
    html_sin_estilos = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.DOTALL)
    lineas = [linea.strip() for linea in strip_tags(html_sin_estilos).splitlines() if linea.strip()]
    texto_plano = "\n".join(lineas)
    asunto = ctx.get("asunto", config["asunto_default"])

    return asunto, texto_plano, html