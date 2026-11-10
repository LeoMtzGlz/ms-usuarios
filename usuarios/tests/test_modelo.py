import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from usuarios.models import Estado, Rol, Usuario
from usuarios.telefono import normalizar_telefono

from .factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_create_user_guarda_correo_en_minusculas_y_password_con_hash():
    usuario = Usuario.objects.create_user("  Ana@Ejemplo.COM ", "Secreta123")
    assert usuario.email == "ana@ejemplo.com"
    assert usuario.password != "Secreta123"
    assert usuario.check_password("Secreta123")


def test_valores_por_defecto():
    usuario = Usuario.objects.create_user("nuevo@ejemplo.com", "Secreta123")
    assert usuario.rol == Rol.CLIENTE
    assert usuario.estado == Estado.PENDIENTE
    assert usuario.is_active is True  # pendiente sigue activo para poder decir cuenta_pendiente
    assert usuario.token_version == 0


def test_correo_duplicado_con_otras_mayusculas_falla_en_la_base():
    Usuario.objects.create_user("ana@ejemplo.com", "Secreta123")
    with pytest.raises(IntegrityError):
        Usuario.objects.create_user("ANA@ejemplo.com", "Secreta123")


def test_telefono_se_normaliza_a_e164():
    assert normalizar_telefono("443 123 4567") == "+524431234567"
    assert normalizar_telefono("+52 (443) 123-4567") == "+524431234567"


def test_telefono_invalido_falla():
    with pytest.raises(ValidationError):
        normalizar_telefono("123")
    usuario = UsuarioFactory.build(telefono="4431234567")  # sin normalizar
    with pytest.raises(ValidationError):
        usuario.full_clean(exclude=["password"])


def test_telefono_duplicado_falla():
    UsuarioFactory(telefono="+524431234567")
    with pytest.raises(IntegrityError):
        UsuarioFactory(telefono="+524431234567")


def test_create_superuser_es_administrador_activo():
    admin = Usuario.objects.create_superuser("admin@ejemplo.com", "Secreta123")
    assert admin.rol == Rol.ADMINISTRADOR
    assert admin.estado == Estado.ACTIVO
    assert admin.is_staff and admin.is_superuser


def test_cambiar_estado_a_inactivo_cierra_sesiones():
    usuario = UsuarioFactory()
    usuario.cambiar_estado(Estado.INACTIVO)
    usuario.refresh_from_db()
    assert usuario.is_active is False
    assert usuario.token_version == 1


def test_reactivar_vuelve_a_permitir_el_acceso_sin_cambiar_token_version():
    usuario = UsuarioFactory()
    usuario.cambiar_estado(Estado.INACTIVO)
    usuario.cambiar_estado(Estado.ACTIVO)
    usuario.refresh_from_db()
    assert usuario.is_active is True
    assert usuario.token_version == 1


def test_cambiar_estado_rechaza_estados_desconocidos():
    with pytest.raises(ValueError):
        UsuarioFactory().cambiar_estado("borrado")
