"""t-02 / st-67: aceptación del aviso de privacidad.

Un solo lugar para saber qué se guarda cuando alguien acepta el aviso:
la fecha y hora (acepto_privacidad_en) y la versión vigente (version_privacidad),
que se toma de settings.VERSION_AVISO_PRIVACIDAD y nunca de lo que mande el cliente.
"""
from django.conf import settings
from django.core import checks
from django.utils import timezone


def version_vigente() -> str:
    """Versión del aviso de privacidad que está publicada ahora."""
    return settings.VERSION_AVISO_PRIVACIDAD


# t-29/st-201: Función auxiliar para el login, que determina si el usuario debe aceptar el aviso.
def requiere_aceptar_privacidad(usuario) -> bool:
    """Devuelve True si la versión del usuario no coincide con la versión vigente."""
    version_usuario = getattr(usuario, "version_privacidad", None)
    return version_usuario != version_vigente()


def datos_aceptacion_privacidad() -> dict:
    """Campos del usuario que registran la aceptación: fecha actual y versión vigente."""
    return {
        "acepto_privacidad_en": timezone.now(),
        "version_privacidad": version_vigente(),
    }


@checks.register()
def revisar_version_aviso_privacidad(app_configs=None, **kwargs):
    """Avisa al arrancar si VERSION_AVISO_PRIVACIDAD no se podría guardar en la base."""
    from usuarios.models import Usuario

    version = getattr(settings, "VERSION_AVISO_PRIVACIDAD", "")
    maximo = Usuario._meta.get_field("version_privacidad").max_length

    if not isinstance(version, str) or not version.strip():
        return [
            checks.Error(
                "VERSION_AVISO_PRIVACIDAD está vacía.",
                hint="Define la versión vigente del aviso en .env, por ejemplo VERSION_AVISO_PRIVACIDAD=1.0",
                id="usuarios.E001",
            )
        ]
    if len(version) > maximo:
        return [
            checks.Error(
                f"VERSION_AVISO_PRIVACIDAD tiene {len(version)} caracteres; el máximo es {maximo}.",
                hint="Usa una versión corta, por ejemplo 1.0 o 2026-1.",
                id="usuarios.E002",
            )
        ]
    return []