"""Normalización de teléfonos al formato internacional E.164 (+52...)."""
import phonenumbers
from django.core.exceptions import ValidationError

REGION_POR_DEFECTO = "MX"

def normalizar_telefono(valor: str, region: str = REGION_POR_DEFECTO) -> str:
    """Convierte '443 123 4567' o '+52 443 123 4567' en '+524431234567'.

    Lanza ValidationError si el número no es válido.
    """
    try:
        numero = phonenumbers.parse(str(valor), region)
    except phonenumbers.NumberParseException as error:
        raise ValidationError("El teléfono no tiene un formato válido.", code="telefono_invalido") from error
    if not phonenumbers.is_valid_number(numero):
        raise ValidationError("El teléfono no es un número válido.", code="telefono_invalido")
    return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)


def validar_telefono_e164(valor: str) -> None:
    """Validador de modelo: el valor guardado ya debe venir normalizado."""
    if normalizar_telefono(valor) != valor:
        raise ValidationError(
            "El teléfono debe guardarse en formato E.164 (+52...).", code="telefono_invalido"
        )
