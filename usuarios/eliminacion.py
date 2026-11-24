"""HU-23 / ST-174: eliminar la cuenta propia (confirmación por correo y anonimización)."""
import logging

from django.db import transaction

from comun.errores import UnicoAdministrador
from comun.roles import Rol
from notificaciones.canales import CanalCorreo
from notificaciones.plantillas import renderizar_plantilla_correo
from usuarios.anonimizacion import anonimizar_usuario
from usuarios.models import Estado, Usuario

logger = logging.getLogger(__name__)


def verificar_no_es_unico_administrador(usuario):
    """El único administrador activo no puede eliminarse: el sistema quedaría sin administración."""
    if usuario.rol != Rol.ADMINISTRADOR:
        return
    # Se bloquean las filas de administradores para que dos eliminaciones simultáneas no se crucen
    otros = (
        Usuario.objects.select_for_update()
        .filter(rol=Rol.ADMINISTRADOR, estado=Estado.ACTIVO)
        .exclude(pk=usuario.pk)
    )
    if not otros.exists():
        raise UnicoAdministrador()


def enviar_confirmacion(correo_original, nombre):
    """Avisa por correo al correo ORIGINAL, antes de anonimizar.

    Se envía directo (sin bandeja) porque el worker lee `usuario.email` al enviar y, tras
    anonimizar, esa dirección ya no existe (ST-172 §4.1, opción B). Si el envío falla se
    registra en el log y la eliminación sigue (HU-27: un aviso no debe bloquear la acción).
    """
    try:
        asunto, texto, html = renderizar_plantilla_correo("cuenta_eliminada", {"nombre": nombre})
        CanalCorreo().enviar(correo_original, asunto, texto, html)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo enviar el correo de confirmación de eliminación")


def eliminar_cuenta(usuario, request=None):
    """Orden de ST-172 §3: regla del administrador, correo de confirmación y anonimización."""
    with transaction.atomic():
        verificar_no_es_unico_administrador(usuario)
        correo_original = usuario.email
        nombre = usuario.first_name
        enviar_confirmacion(correo_original, nombre)
        anonimizar_usuario(usuario, request=request)