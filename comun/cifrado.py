#t-30/st-205
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    clave = settings.CLAVE_CIFRADO_2FA

    if not clave:
        raise ValueError(
            "CLAVE_CIFRADO_2FA no está configurada. "
            "Genera una clave Fernet y agrégala al archivo .env."
        )

    return Fernet(clave.encode())


def cifrar(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()