from django.conf import settings
from .models import Notificacion, CanalNotificacion
from .canales import CanalConsola


def obtener_canal() -> CanalConsola:
    """Devuelve el canal configurado en los settings."""
    canal_setting = getattr(settings, "CANAL_NOTIFICACIONES", "consola")

    if canal_setting == CanalNotificacion.CONSOLA:
        return CanalConsola()

    # Aquí Alondra (T-08) y quien haga WhatsApp (T-09) agregarán sus clases
    return CanalConsola()


def notificar(usuario, plantilla: str, contexto: dict, canal: str = None) -> Notificacion:
    """
    Guarda una notificación en la bandeja de salida.
    """
    if not canal:
        canal = usuario.canal_preferido

    # Validación solicitada por el profesor
    if canal not in CanalNotificacion.values:
        raise ValueError(f"Canal desconocido: {canal}")

    notificacion = Notificacion.objects.create(
        destinatario=usuario,
        canal=canal,
        plantilla=plantilla,
        contexto=contexto,
        estado=Notificacion.ESTADO_PENDIENTE,
    )
    return notificacion