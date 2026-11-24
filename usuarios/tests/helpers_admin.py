"""Ayudantes de prueba para las vistas de administración (t-17/st-149, t-17/st-150, t-15/st-143, t-19/st-157)."""
from rest_framework.test import APIClient

from comun.roles import Rol
from usuarios.tests.factories import UsuarioFactory
from usuarios.tokens import CustomTokenObtainPairSerializer


def crear_usuario(rol=Rol.CLIENTE, **campos):
    """Usuario activo con contraseña PASSWORD_PRUEBA (ver factories.py)."""
    return UsuarioFactory(rol=rol, **campos)


def api_de(usuario):
    """APIClient con un token que lleva los claims reales de HU-05 (rol, debe_cambiar_password...).

    Requiere el fixture `llaves` de conftest.py para firmar con RS256.
    """
    acceso = CustomTokenObtainPairSerializer.get_token(usuario).access_token
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return cliente