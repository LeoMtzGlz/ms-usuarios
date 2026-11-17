"""Códigos de 6 dígitos de un solo uso (HU-02 / HU-03).

Mínimo necesario para HU-02/ST-66: crear el código de activación al registrarse.
La verificación del código (validar, contar intentos, expirar) llega con HU-03 (ST-71/ST-72).
"""
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from usuarios.models import CodigoVerificacion

MINUTOS_VIGENCIA = 10


def generar_codigo() -> str:
    """6 dígitos con ceros a la izquierda, con un generador criptográfico."""
    return f"{secrets.randbelow(10**6):06d}"


def crear_codigo(usuario, proposito, canal=None):
    """Crea un código nuevo y anula los pendientes del mismo propósito.

    Devuelve (registro, codigo_en_claro). En la base solo se guarda el hash;
    el código en claro solo existe aquí para mandárselo a la persona.
    Se llama dentro de la transacción de quien la usa.
    """
    canal = canal or usuario.canal_preferido
    codigo = generar_codigo()
    CodigoVerificacion.objects.filter(usuario=usuario, proposito=proposito, usado=False).update(usado=True)
    registro = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=proposito,
        canal=canal,
        codigo_hash=make_password(codigo),
        expira_en=timezone.now() + timedelta(minutes=MINUTOS_VIGENCIA),
    )
    return registro, codigo