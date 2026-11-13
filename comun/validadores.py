"""Validadores de contraseña propios de svc-usuarios (T-12).

Se registran en settings.AUTH_PASSWORD_VALIDATORS (USR-102) y los aplica
validate_password() en registro, recuperación, cambio y alta de usuarios.
"""
from django.core.exceptions import ValidationError

DIGITOS = "0123456789"

AYUDA_POLITICA_PASSWORD = (
    "Mínimo 8 caracteres, con al menos una letra mayúscula y un número. "
    "No puede ser una contraseña común ni parecerse a tu correo o nombre."
)

class MayusculaYNumeroValidator:
    """Exige al menos una letra mayúscula y al menos un dígito (0-9)."""

    def validate(self, password, user=None):
        errores = []
        if not any(c.isupper() for c in password):  # acepta Á, Ñ, etc.
            errores.append(ValidationError(
                "La contraseña debe incluir al menos una letra mayúscula.",
                code="password_sin_mayuscula",
            ))
        if not any(c in DIGITOS for c in password):  # evita contar '²' como número
            errores.append(ValidationError(
                "La contraseña debe incluir al menos un número.",
                code="password_sin_numero",
            ))
        if errores:
            raise ValidationError(errores)

    def get_help_text(self):
        return "Tu contraseña debe incluir al menos una letra mayúscula y un número."