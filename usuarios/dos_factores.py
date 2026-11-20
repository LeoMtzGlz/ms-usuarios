#t-30/st-206
"""Ayudas para la verificación en dos pasos (HU-30)."""
import base64
import io

import qrcode


def qr_base64(uri: str) -> str:
    """Devuelve el QR de la URI otpauth:// como PNG en base64 (sin prefijo data:)."""
    imagen = qrcode.make(uri)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()