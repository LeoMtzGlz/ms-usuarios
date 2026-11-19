"""Códigos de 6 dígitos de un solo uso (HU-02 / HU-03).

generar_codigo() es el punto de entrada: crea el código, guarda solo su hash y
encola la notificación. La verificación (validar, contar intentos, expirar) es ST-72.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from notificaciones.services import notificar
from usuarios.models import Canal, CodigoVerificacion, Proposito

PLANTILLAS = {
    Proposito.ACTIVACION: "codigo_activacion",
    Proposito.RECUPERACION: "codigo_recuperacion",
    Proposito.CAMBIO_CONTACTO: "codigo_cambio_contacto",
}


def sortear_codigo() -> str:
    """6 dígitos con ceros a la izquierda, con un generador criptográfico."""
    return f"{secrets.randbelow(10**6):06d}"


def elegir_canal(usuario, canal=None) -> str:
    """Canal indicado, o el preferido. WhatsApp sin teléfono se cambia a correo."""
    canal = canal or usuario.canal_preferido
    if canal not in Canal.values:
        raise ValueError(f"Canal desconocido: {canal}")
    if canal == Canal.WHATSAPP and not usuario.telefono:
        return str(Canal.CORREO)
    return str(canal)


def crear_codigo(usuario, proposito, canal=None):
    """Crea un código nuevo y anula los pendientes del mismo propósito.

    Devuelve (registro, codigo_en_claro). En la base solo se guarda el hash;
    el código en claro solo existe aquí para mandárselo a la persona.
    """
    canal = elegir_canal(usuario, canal)
    codigo = sortear_codigo()
    CodigoVerificacion.objects.filter(usuario=usuario, proposito=proposito, usado=False).update(usado=True)
    registro = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=proposito,
        canal=canal,
        codigo_hash=make_password(codigo),
        expira_en=timezone.now() + timedelta(minutes=settings.CODIGO_MINUTOS),
    )
    return registro, codigo


def generar_codigo(usuario, proposito, canal=None) -> CodigoVerificacion:
    """Crea el código y encola la notificación en la misma transacción.

    Si falla el encolado, tampoco queda el código. Devuelve el registro, nunca
    el código en claro.
    """
    with transaction.atomic():
        registro, codigo = crear_codigo(usuario, proposito, canal)
        notificar(
            usuario,
            plantilla=PLANTILLAS[proposito],
            contexto={"codigo": codigo, "nombre": usuario.first_name, "minutos": settings.CODIGO_MINUTOS},
            canal=registro.canal,
        )
    return registro
