import pytest
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from usuarios.tokens import CustomTokenObtainPairSerializer
from usuarios.models import Usuario, Estado
from comun.errores import CuentaPendiente, CuentaInactiva, CredencialesInvalidas

@pytest.fixture
def factory():
    return APIRequestFactory()

@pytest.fixture
def request_valido(factory):
    request = factory.post("/api/v1/auth/login/")
    request.user = AnonymousUser()
    return request


@override_settings(SIMPLE_JWT={
    "ALGORITHM": "HS256",
    "SIGNING_KEY": "clave-de-prueba-super-secreta-y-muy-larga-para-que-no-salte-el-warning",
})
@pytest.mark.django_db
def test_login_correcto_con_claims(request_valido):
    Usuario.objects.create_user(
        email="activo@ejemplo.com", password="Password123", estado=Estado.ACTIVO
    )
    
    serializer = CustomTokenObtainPairSerializer(
        data={"email": "activo@ejemplo.com", "password": "Password123"},
        context={"request": request_valido}
    )
    assert serializer.is_valid(), serializer.errors
    data = serializer.validated_data
    
    assert "access" in data
    assert "refresh" in data
    assert data["usuario"]["rol"] == "cliente"

@pytest.mark.django_db
def test_login_credenciales_invalidas(request_valido):
    serializer = CustomTokenObtainPairSerializer(
        data={"email": "noexiste@ejemplo.com", "password": "Password123"},
        context={"request": request_valido}
    )
    with pytest.raises(CredencialesInvalidas):
        serializer.is_valid(raise_exception=True)

@pytest.mark.django_db
def test_login_cuenta_pendiente(request_valido):
    Usuario.objects.create_user(
        email="pendiente@ejemplo.com", password="Password123", estado=Estado.PENDIENTE
    )
    serializer = CustomTokenObtainPairSerializer(
        data={"email": "pendiente@ejemplo.com", "password": "Password123"},
        context={"request": request_valido}
    )
    with pytest.raises(CuentaPendiente):
        serializer.is_valid(raise_exception=True)

@pytest.mark.django_db
def test_login_cuenta_inactiva(request_valido):
    Usuario.objects.create_user(
        email="inactivo@ejemplo.com", password="Password123", estado=Estado.INACTIVO, is_active=False
    )
    serializer = CustomTokenObtainPairSerializer(
        data={"email": "inactivo@ejemplo.com", "password": "Password123"},
        context={"request": request_valido}
    )
    with pytest.raises(CuentaInactiva):
        serializer.is_valid(raise_exception=True)