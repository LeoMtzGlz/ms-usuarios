"""Conversión de la llave pública RS256 al formato JWKS de T-14/ST-135."""

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _base64url_entero(valor):
    longitud = max(1, (valor.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(valor.to_bytes(longitud, "big")).rstrip(b"=").decode()


def jwks_desde_pem(contenido_pem):
    """Devuelve una JWKS con una sola llave RSA pública y un identificador estable."""
    llave = serialization.load_pem_public_key(contenido_pem.encode())
    if not isinstance(llave, rsa.RSAPublicKey):
        raise ValueError("La llave configurada no es RSA.")

    der = llave.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b"=").decode()
    numeros = llave.public_numbers()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": _base64url_entero(numeros.n),
                "e": _base64url_entero(numeros.e),
            }
        ]
    }
