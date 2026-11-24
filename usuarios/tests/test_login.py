import pytest
from usuarios.models import Usuario, Estado

@pytest.fixture
def usuario_activo(db):
    return Usuario.objects.create_user(
        email="activo@ejemplo.com", password="Password123", estado=Estado.ACTIVO
    )

@pytest.mark.django_db
def test_login_exitoso(api_client, usuario_activo, llaves): # <--- 'llaves' agregado
    response = api_client.post('/api/v1/auth/login/', {"email": "activo@ejemplo.com", "password": "Password123"})
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    assert "usuario" in response.data

@pytest.mark.django_db
def test_login_credenciales_invalidas(api_client):
    response = api_client.post('/api/v1/auth/login/', {"email": "noexiste@ejemplo.com", "password": "Password123"})
    assert response.status_code == 401
    assert response.data["codigo"] == "credenciales_invalidas"

@pytest.mark.django_db
def test_login_cuenta_pendiente(api_client, db):
    Usuario.objects.create_user(email="pendiente@ejemplo.com", password="Password123", estado=Estado.PENDIENTE)
    response = api_client.post('/api/v1/auth/login/', {"email": "pendiente@ejemplo.com", "password": "Password123"})
    assert response.status_code == 403
    assert response.data["codigo"] == "cuenta_pendiente"

@pytest.mark.django_db
def test_login_cuenta_inactiva(api_client, db):
    Usuario.objects.create_user(
        email="inactivo@ejemplo.com", 
        password="Password123", 
        estado=Estado.INACTIVO, 
        is_active=False
    )
    response = api_client.post('/api/v1/auth/login/', {"email": "inactivo@ejemplo.com", "password": "Password123"})
    assert response.status_code == 403
    assert response.data["codigo"] == "cuenta_inactiva"

# ST-194: Respuestas idénticas para cuenta existente e inexistente.
@pytest.mark.django_db
def test_login_respuesta_igual_cuenta_existente_o_inexistente(
    api_client, usuario_activo
):
    respuesta_existente = api_client.post(
        "/api/v1/auth/login/",
        {
            "email": "activo@ejemplo.com",
            "password": "PasswordIncorrecta123",
        },
    )

    respuesta_inexistente = api_client.post(
        "/api/v1/auth/login/",
        {
            "email": "noexiste@ejemplo.com",
            "password": "PasswordIncorrecta123",
        },
    )

    assert respuesta_existente.status_code == 401
    assert respuesta_inexistente.status_code == 401
    assert respuesta_existente.data == respuesta_inexistente.data