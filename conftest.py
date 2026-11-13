"""Fixtures compartidos por las pruebas de todas las apps (t-06/st-28).

pytest carga este archivo automáticamente: cualquier prueba puede pedir
`api_client` o `usuario` como parámetro sin importarlos.
"""
import pytest
from rest_framework.test import APIClient

from usuarios.tests.factories import UsuarioFactory


@pytest.fixture
def api_client():
    """Cliente de DRF sin sesión iniciada."""
    return APIClient()


@pytest.fixture
def usuario(db):
    """Usuario activo guardado en la base, con contraseña PASSWORD_PRUEBA."""
    return UsuarioFactory()
