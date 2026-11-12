"""Generación y verificación de códigos de 6 dígitos (HU-03).

Sirve para activación, recuperación y cambio de contacto: cambia solo `proposito`.
"""
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from comun.errores import CodigoExpirado, CodigoInvalido
from usuarios.models import CodigoVerificacion

MINUTOS_VIGENCIA = 10
MAX_INTENTOS = 5


def generar_codigo() -> str:
    """6 dígitos con ceros a la izquierda, con generador criptográfico."""
    return f"{secrets.randbelow(10**6):06d}"


def crear_codigo(usuario, proposito, canal=None):
    """Crea un código nuevo e invalida los anteriores pendientes del mismo propósito.

    Devuelve (registro, codigo_en_claro). El código en claro solo existe aquí:
    se manda al usuario y no se guarda.
    """
    canal = canal or usuario.canal_preferido
    codigo_plano = generar_codigo()
    with transaction.atomic():
        CodigoVerificacion.objects.filter(
            usuario=usuario, proposito=proposito, usado=False
        ).update(usado=True)
        registro = CodigoVerificacion.objects.create(
            usuario=usuario,
            proposito=proposito,
            canal=canal,
            codigo_hash=make_password(codigo_plano),
            expira_en=timezone.now() + timedelta(minutes=MINUTOS_VIGENCIA),
        )
    return registro, codigo_plano


def verificar_codigo(usuario, proposito, codigo_ingresado):
    """Valida el código. Devuelve el registro usado o lanza CodigoInvalido / CodigoExpirado."""
    # Las excepciones se lanzan FUERA del atomic: si no, el rollback borraría el conteo de intentos.
    with transaction.atomic():
        codigo = (
            CodigoVerificacion.objects.select_for_update()
            .filter(usuario=usuario, proposito=proposito, usado=False)
            .order_by("-creado_en")
            .first()
        )
        if codigo is None or codigo.expira_en <= timezone.now():
            resultado = "expirado"
        elif check_password(codigo_ingresado, codigo.codigo_hash):
            codigo.usado = True
            codigo.save(update_fields=["usado"])
            resultado = "ok"
        else:
            codigo.intentos += 1
            if codigo.intentos >= MAX_INTENTOS:
                codigo.usado = True  # se anula: ya no sirve ni el correcto
            codigo.save(update_fields=["intentos", "usado"])
            resultado = "invalido"

    if resultado == "expirado":
        raise CodigoExpirado()
    if resultado == "invalido":
        raise CodigoInvalido()
    return codigo