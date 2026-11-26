import pytest
from django.contrib.auth import get_user_model
from usuarios.models import Estado, Proposito
from usuarios.codigos import crear_codigo  # <-- Aquí estaba el detalle
from usuarios.tests.factories import UsuarioFactory

Usuario = get_user_model()
URL = "/api/v1/auth/restablecer/"

@pytest.mark.django_db
def test_restablecer_exitoso(api_client):
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    _, codigo = crear_codigo(usuario, Proposito.RECUPERACION)

    response = api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": codigo,
        "password": "NuevaPassword123",
        "password_confirmacion": "NuevaPassword123"
    })

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password("NuevaPassword123")
    assert usuario.token_version > 0