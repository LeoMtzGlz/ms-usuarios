"""HU-10 / ST-107: lógica de la solicitud de recuperación de contraseña."""
import logging

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from usuarios.codigos import generar_codigo
from usuarios.models import Estado, Proposito, Usuario
from usuarios.telefono import normalizar_telefono

logger = logging.getLogger(__name__)

# Misma respuesta exista o no la cuenta: no se puede enumerar quién está registrado.
MENSAJE_RECUPERACION = "Si la cuenta existe, te enviamos un código."


def buscar_usuario(identificador):
    """Devuelve la cuenta (activa o pendiente) que corresponde al correo o teléfono, o None."""
    identificador = identificador.strip()
    consulta = Usuario.objects.filter(estado__in=[Estado.ACTIVO, Estado.PENDIENTE])
    if "@" in identificador:
        return consulta.filter(email__iexact=identificador).first()
    try:
        telefono = normalizar_telefono(identificador)
    except DjangoValidationError:
        return None
    return consulta.filter(telefono=telefono).first()


def solicitar_recuperacion(identificador, canal=None):
    """Genera y encola el código de recuperación si la cuenta existe. Nunca lanza ni revela nada.

    - Cuenta inexistente o inactiva: no se envía nada, pero se hace un trabajo de costo parecido
      (un hash) para que el tiempo de respuesta no delate si existe.
    - Cuenta pendiente: también recibe código; al restablecer (HU-10, ST-108) se activa.
    - Si falla el envío se registra en el log y se responde igual (HU-27).
    Devuelve el usuario al que se le envió el código, o None.
    """
    usuario = buscar_usuario(identificador)
    if usuario is None:
        make_password("trabajo-de-relleno")
        return None
    try:
        with transaction.atomic():
            generar_codigo(usuario, Proposito.RECUPERACION, canal)
    except Exception:
        logger.exception("No se pudo generar el código de recuperación (usuario %s)", usuario.pk)
        return None
    return usuario