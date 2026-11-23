
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from comun.roles import Rol
from usuarios.models import Estado, Usuario, Zona
from usuarios.serializers_admin import AltaUsuarioSerializer
from usuarios.tokens import CustomTokenObtainPairSerializer

pytestmark = pytest.mark.django_db


def test_asignar_zona_a_usuario_operativo():
    zona = Zona.objects.create(nombre="Zona Norte")

    serializer = AltaUsuarioSerializer(data={
        "nombre": "Alondra",
        "apellidos": "Lopez",
        "correo": "alondra@example.com",
        "telefono": "+524431001234",
        "zona": zona.id,
    })

    assert serializer.is_valid(), serializer.errors

    usuario = serializer.save(contrasena="Temporal123")

    assert usuario.zona == zona
    assert usuario.rol == Rol.OPERATIVO
    assert usuario.estado == Estado.ACTIVO


def test_no_permitir_asignar_zona_inactiva():
    zona = Zona.objects.create(
        nombre="Zona Inactiva",
        activa=False,
    )

    serializer = AltaUsuarioSerializer(data={
        "nombre": "Usuario",
        "apellidos": "Prueba",
        "correo": "prueba@example.com",
        "telefono": "+524431001235",
        "zona": zona.id,
    })

    assert not serializer.is_valid()
    assert "zona" in serializer.errors


def test_token_incluye_identificador_de_zona(llaves):
    zona = Zona.objects.create(nombre="Zona Sur")

    usuario = Usuario.objects.create_user(
        email="operativo@example.com",
        password="Password123",
        rol=Rol.OPERATIVO,
        estado=Estado.ACTIVO,
        zona=zona,
    )

    token = CustomTokenObtainPairSerializer.get_token(usuario)
    acceso = AccessToken(str(token.access_token))

    assert acceso["zona_id"] == zona.id
