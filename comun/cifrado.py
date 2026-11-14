#t-30/st-205
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    return Fernet(settings.CLAVE_CIFRADO_2FA.encode())


def cifrar(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()