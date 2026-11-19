from django.conf import settings
from .models import Notificacion, CanalNotificacion
from .canales import Canal, CanalConsola, CanalCorreo

# t-10/st-51: clase que envía cada canal. T-09 agrega aquí CanalWhatsApp.
CLASES_CANAL = {
    CanalNotificacion.CONSOLA: CanalConsola,
    CanalNotificacion.CORREO: CanalCorreo,
}


def obtener_canal(canal: str | None = None) -> Canal:
    """Devuelve el canal por el que sale una notificación.

    t-10/st-51: recibe el canal de cada notificación (``notificacion.canal``).
    - Con CANAL_NOTIFICACIONES=consola (desarrollo) todo sale por consola, sin importar ``canal``.
    - Si no, usa ``canal``; si no se pasa, el del setting (como antes).
    - Si el canal aún no tiene clase (WhatsApp antes de T-09) lanza ValueError: el worker la
      marca fallida en lugar de mandarla en silencio por otro medio.
    """
    canal_setting = getattr(settings, "CANAL_NOTIFICACIONES", CanalNotificacion.CONSOLA)
    if canal_setting == CanalNotificacion.CONSOLA:
        return CanalConsola()

    canal = canal or canal_setting
    clase = CLASES_CANAL.get(canal)
    if clase is None:
        raise ValueError(f"No hay canal disponible para: {canal}")
    return clase()


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