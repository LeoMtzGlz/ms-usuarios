"""Fixtures compartidos por las pruebas de todas las apps (t-06/st-28).

pytest carga este archivo automáticamente: cualquier prueba puede pedir
`api_client`, `usuario` o `llaves` como parámetro sin importarlos.
"""
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework.test import APIClient
from rest_framework_simplejwt import state
from rest_framework_simplejwt.backends import TokenBackend

from usuarios.tests.factories import UsuarioFactory


@pytest.fixture
def api_client():
    """Cliente de DRF sin sesión iniciada."""
    return APIClient()


@pytest.fixture
def usuario(db):
    """Usuario activo guardado en la base, con contraseña PASSWORD_PRUEBA."""
    return UsuarioFactory()


@pytest.fixture
def llaves(monkeypatch):
    """Par RS256 temporal para firmar y verificar tokens sin usar llaves/*.pem.

    Devuelve (privada_pem, publica_pem).
    """
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privada_pem = privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    publica_pem = (
        privada.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    backend = TokenBackend("RS256", signing_key=privada_pem, verifying_key=publica_pem, issuer="svc-usuarios")
    monkeypatch.setattr(state, "token_backend", backend)
    return privada_pem, publica_pem


# ST-185: Desactivar Axes por defecto para aislar las pruebas no relacionadas.
@pytest.fixture(autouse=True)
def axes_desactivado_por_defecto(settings):
    settings.AXES_ENABLED = False


# ST-185: Habilitar Axes explícitamente en las pruebas de bloqueo.
@pytest.fixture
def axes_habilitado(axes_desactivado_por_defecto, settings):
    settings.AXES_ENABLED = True
