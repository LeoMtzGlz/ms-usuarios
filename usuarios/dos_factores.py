#t-30/st-206
"""Ayudas para la verificación en dos pasos (HU-30)."""
import secrets # t-30/st-207
import qrcode
import base64
import io

# t-3-/st-207
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from usuarios.models import CodigoRespaldo # t-30/st-207

ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin 0, O, 1, I, L
CANTIDAD = 10 #? La cantidad de codigos de respaldo
LONGITUD = 6 #? Cambia el tamaño del codigo de respaldo

def qr_base64(uri: str) -> str: #t-30/st-206
    """Devuelve el QR de la URI otpauth:// como PNG en base64 (sin prefijo data:)."""
    imagen = qrcode.make(uri)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def normalizar_codigo(codigo: str) -> str: # t-30/st-207
    return codigo.replace("-", "").replace(" ", "").upper()


def _nuevo_codigo() -> str: # t-30/st-207
    MITAD_RANGO = int(LONGITUD / 2)
    crudo = "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD))
    return f"{crudo[:MITAD_RANGO]}-{crudo[MITAD_RANGO:]}"

@transaction.atomic
def generar_codigos_respaldo(usuario, cantidad: int = CANTIDAD) -> list[str]:
    """Reemplaza los códigos del usuario y devuelve los nuevos EN CLARO.

    Es la única vez que existen en claro: el endpoint los entrega en la respuesta
    y no se vuelven a mostrar.
    """
    CodigoRespaldo.objects.filter(usuario=usuario).delete()

    codigos: set[str] = set()
    while len(codigos) < cantidad:
        codigos.add(_nuevo_codigo())
    codigos_lista = sorted(codigos)

    CodigoRespaldo.objects.bulk_create([
        CodigoRespaldo(usuario=usuario, codigo_hash=make_password(normalizar_codigo(c)))
        for c in codigos_lista
    ])
    return codigos_lista

@transaction.atomic
def usar_codigo_respaldo(usuario, codigo: str) -> bool:
    """Valida y consume un código (un solo uso). Para HU-31."""
    normal = normalizar_codigo(codigo)
    pendientes = (CodigoRespaldo.objects
                  .select_for_update()
                  .filter(usuario=usuario, usado_en__isnull=True))
    for cr in pendientes:
        if check_password(normal, cr.codigo_hash):
            cr.usado_en = timezone.now()
            cr.save(update_fields=["usado_en"])
            return True
    return False