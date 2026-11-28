from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from .models import Notificacion, CanalNotificacion
from .canales import Canal, CanalConsola, CanalCorreo
from .plantillas import ALIAS_PLANTILLAS, PLANTILLAS_CORREO, renderizar_plantilla_correo

# t-10/st-51: clase que envía cada canal. T-09 agrega aquí CanalWhatsApp.
CLASES_CANAL = {
    CanalNotificacion.CONSOLA: CanalConsola,
    CanalNotificacion.CORREO: CanalCorreo,
}


def obtener_canal(canal: str | None = None) -> Canal:
    """Devuelve el canal por el que sale una notificación."""
    canal_setting = getattr(settings, "CANAL_NOTIFICACIONES", CanalNotificacion.CONSOLA)
    if canal_setting == CanalNotificacion.CONSOLA:
        return CanalConsola()

    canal = canal or canal_setting
    clase = CLASES_CANAL.get(canal)
    if clase is None:
        raise ValueError(f"No hay canal disponible para: {canal}")
    return clase()


# T-08/ST-42: Prepara asunto, texto plano y HTML desde las 5 plantillas de correo
def preparar_contenido_notificacion(notificacion: Notificacion) -> tuple[str, str, str | None]:
    """
    Devuelve (asunto, texto, html) listos para pasar a canal.enviar(...).
    Si la plantilla pertenece a PLANTILLAS_CORREO (o sus alias), renderiza su versión HTML y texto plano.
    """
    clave = ALIAS_PLANTILLAS.get(notificacion.plantilla, notificacion.plantilla)
    if clave in PLANTILLAS_CORREO:
        return renderizar_plantilla_correo(clave, notificacion.contexto)

    asunto = notificacion.contexto.get("asunto", f"Notificación: {notificacion.plantilla}")
    texto = notificacion.contexto.get("texto", str(notificacion.contexto))
    return asunto, texto, None


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


# t-11/st-56: Contar las notificaciones enviadas hoy por canal
def contar_envios_hoy(canal: str) -> int:
    """Devuelve la cantidad de notificaciones enviadas hoy por el canal indicado.

    "Hoy" es el día local (TIME_ZONE). Se filtra por rango [inicio del día, inicio del día siguiente)
    en lugar de ``__date`` para que PostgreSQL no convierta la fecha de cada fila.
    """
    inicio = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    return Notificacion.objects.filter(
        canal=canal,
        estado=Notificacion.ESTADO_ENVIADA,
        actualizado_en__gte=inicio,
        actualizado_en__lt=inicio + timedelta(days=1),
    ).count()
