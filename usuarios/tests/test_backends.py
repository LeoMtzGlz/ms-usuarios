import pytest
from django.contrib.auth import authenticate
from usuarios.models import Usuario

@pytest.fixture
def usuario_activo(db):
    return Usuario.objects.create_user(
        email="test@ejemplo.com",
        telefono="+524431234567",
        password="Password123",
        estado="activo"
    )

@pytest.mark.django_db
def test_login_con_correo_exacto(usuario_activo):
    # Probamos la función authenticate directamente
    user = authenticate(email="test@ejemplo.com", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_correo_mayusculas(usuario_activo):
    # authenticate debe encontrar el correo aunque tenga mayúsculas
    user = authenticate(email="TEST@EJEMPLO.COM", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_telefono_local(usuario_activo):
    # authenticate debe normalizar el teléfono
    user = authenticate(username="4431234567", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_password_incorrecta(usuario_activo):
    user = authenticate(email="test@ejemplo.com", password="Incorrecta123")
    assert user is None

@pytest.mark.django_db
def test_login_con_usuario_inexistente(db):
    # Cuando no existe, debe tardar un poco (por el set_password) y devolver None
    user = authenticate(email="noexiste@ejemplo.com", password="Password123")
    assert user is None