"""Códigos de 6 dígitos de un solo uso (HU-02 / HU-03).

generar_codigo() es el punto de entrada: crea el código, guarda solo su hash y
encola la notificación. La verificación (validar, contar intentos, expirar) es ST-72.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
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

# ST-72: verificación del código

MAX_INTENTOS = 5

def verificar_codigo(usuario, proposito, codigo_en_claro):
    """Valida un código de 6 dígitos.

    Devuelve el registro si es válido y lo marca como usado.
    Si falla, lanza ValueError con uno de estos códigos:
    codigo_invalido | codigo_expirado | codigo_bloqueado
    """
    registro = (
        CodigoVerificacion.objects.filter(
            usuario=usuario, proposito=proposito, usado=False
        )
        .order_by("-id")
        .first()
    )

    if registro is None:
        raise ValueError("codigo_invalido")

    # 1. ¿Ya venció?
    if timezone.now() > registro.expira_en:
        registro.usado = True
        registro.save(update_fields=["usado"])
        raise ValueError("codigo_expirado")

    # 2. ¿Ya agotó los intentos?
    if registro.intentos >= MAX_INTENTOS:
        registro.usado = True
        registro.save(update_fields=["usado"])
        raise ValueError("codigo_bloqueado")

    # 3. ¿El código coincide con el hash?
    if not check_password(codigo_en_claro, registro.codigo_hash):
        registro.intentos += 1
        if registro.intentos >= MAX_INTENTOS:
            registro.usado = True
            registro.save(update_fields=["usado", "intentos"])
            raise ValueError("codigo_bloqueado")
        registro.save(update_fields=["intentos"])
        raise ValueError("codigo_invalido")

    # 4. Correcto: se marca como usado, un solo uso
    registro.usado = True
    registro.save(update_fields=["usado"])
    return registro
