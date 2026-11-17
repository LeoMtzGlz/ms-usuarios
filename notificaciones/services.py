from .models import Notificacion

def notificar(usuario, plantilla: str, contexto: dict, canal: str = None) -> Notificacion:
    """
    Guarda una notificación en la bandeja de salida.
    Si no se especifica canal, usa el canal_preferido del usuario.
    """
    if not canal:
        canal = usuario.canal_preferido

    notificacion = Notificacion.objects.create(
        destinatario=usuario,
        canal=canal,
        plantilla=plantilla,
        contexto=contexto,
        estado=Notificacion.ESTADO_PENDIENTE
    )
    return notificacion