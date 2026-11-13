"""Pruebas mínimas de los fixtures de conftest.py (t-06/st-28)."""
import pytest
from rest_framework.test import APIClient

from usuarios.models import Estado, Usuario

from .factories import PASSWORD_PRUEBA

pytestmark = pytest.mark.django_db


def test_api_client_es_cliente_de_drf_y_consulta_la_api(api_client):
    assert isinstance(api_client, APIClient)
    respuesta = api_client.get("/api/v1/salud/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "bd": "ok"}


def test_usuario_queda_guardado_activo_y_con_password_conocida(usuario):
    assert Usuario.objects.filter(pk=usuario.pk).exists()
    assert usuario.estado == Estado.ACTIVO
    assert usuario.check_password(PASSWORD_PRUEBA)
