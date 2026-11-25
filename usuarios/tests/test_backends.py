import pytest
from django.contrib.auth import authenticate
from usuarios.models import Usuario
from django.test import RequestFactory
from usuarios.axes import obtener_usuario_axes

@pytest.fixture
def request_obj():
    return RequestFactory().post("/api/v1/auth/login/")

@pytest.fixture
def usuario_activo(db):
    return Usuario.objects.create_user(
        email="test@ejemplo.com",
        telefono="+524431234567",
        password="Password123",
        estado="activo"
    )

@pytest.mark.django_db
def test_login_con_correo_exacto(usuario_activo, request_obj):
    # Probamos la función authenticate directamente
    user = authenticate(request_obj, email="test@ejemplo.com", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_correo_mayusculas(usuario_activo, request_obj):
    # authenticate debe encontrar el correo aunque tenga mayúsculas
    user = authenticate(request_obj, email="TEST@EJEMPLO.COM", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_telefono_local(usuario_activo, request_obj):
    # authenticate debe normalizar el teléfono
    user = authenticate(request_obj, username="4431234567", password="Password123")
    assert user == usuario_activo

@pytest.mark.django_db
def test_login_con_password_incorrecta(usuario_activo, request_obj):
    user = authenticate(request_obj, email="test@ejemplo.com", password="Incorrecta123")
    assert user is None

@pytest.mark.django_db
def test_login_con_usuario_inexistente(db, request_obj):
    # Cuando no existe, debe tardar un poco (por el set_password) y devolver None
    user = authenticate(request_obj, email="noexiste@ejemplo.com", password="Password123")
    assert user is None

# ST-183: Regresión para verificar la normalización de identificadores en django-axes.
@pytest.mark.parametrize(
    ("identificador", "esperado"),
    [
        ("Ana@Ejemplo.com", "ana@ejemplo.com"),
        ("ana@ejemplo.com", "ana@ejemplo.com"),
        ("443 123 4567", "+524431234567"),
        ("+52 443 123 4567", "+524431234567"),
    ],
)
def test_obtener_usuario_axes_normaliza_identificadores(
    request_obj, identificador, esperado
):
    resultado = obtener_usuario_axes(
        request_obj,
        {"username": identificador},
    )

    assert resultado == esperado
