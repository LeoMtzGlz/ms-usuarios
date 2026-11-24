import pytest
from rest_framework_simplejwt.tokens import AccessToken
from usuarios.models import Usuario, Estado


@pytest.mark.django_db
def test_login_con_telefono_exitoso(api_client, llaves):
    """Prueba que se pueda iniciar sesión usando el número de teléfono."""
    Usuario.objects.create_user(
        email="telefono@ejemplo.com",
        password="Password123",
        telefono="+524431234567",
        estado=Estado.ACTIVO,
    )

    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "+524431234567", "password": "Password123"},
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_claims_presentes(api_client, llaves):
    """Prueba que el token JWT incluya los claims requeridos por el backlog."""
    # Creamos el usuario directamente aquí (antes usábamos una fixture que no existe aquí)
    Usuario.objects.create_user(
        email="activo@ejemplo.com",
        password="Password123",
        estado=Estado.ACTIVO,
    )

    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "activo@ejemplo.com", "password": "Password123"},
    )

    assert response.status_code == 200

    # Decodificamos el token y verificamos los claims
    token = AccessToken(response.data["access"])

    assert token["user_id"] is not None
    assert token["rol"] == "cliente"
    assert token["email_verificado"] is False
    assert token["token_version"] == 0
    assert token["debe_cambiar_password"] is False