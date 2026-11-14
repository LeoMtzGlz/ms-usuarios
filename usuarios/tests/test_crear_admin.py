"""t-13/st-124: Pruebas del comando crear_admin (T-13, criterio 4)."""

import pytest
from django.core.management import CommandError, call_command

from comun.roles import Rol
from usuarios.models import Estado, Usuario
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Segura123x"


@pytest.fixture
def consola(monkeypatch):
    """Simula lo que se escribe en la consola cuando el comando pide la contraseña."""

    def responder(*valores):
        respuestas = iter(valores)
        monkeypatch.setattr("getpass.getpass", lambda *a, **k: next(respuestas))

    return responder


@pytest.fixture
def eventos(monkeypatch):
    registrados = []
    monkeypatch.setattr(
        "usuarios.management.commands.crear_admin.registrar_evento",
        lambda accion, usuario=None, **detalles: registrados.append((accion, usuario, detalles)),
    )
    return registrados


def test_crea_administrador_activo(consola, eventos):
    """T-13 criterio 4: el primer administrador se crea con un comando."""
    consola(PASSWORD, PASSWORD)
    call_command("crear_admin", "Admin@Ejemplo.com", "--nombre", "Ana", "--apellidos", "López")

    admin = Usuario.objects.get(email="admin@ejemplo.com")
    assert admin.rol == Rol.ADMINISTRADOR
    assert admin.estado == Estado.ACTIVO
    assert admin.is_active and admin.is_staff and admin.is_superuser
    assert admin.email_verificado
    assert (admin.first_name, admin.last_name) == ("Ana", "López")


def test_guarda_la_contrasena_con_argon2(consola, eventos):
    consola(PASSWORD, PASSWORD)
    call_command("crear_admin", "admin@ejemplo.com")

    admin = Usuario.objects.get(email="admin@ejemplo.com")
    assert admin.password.startswith("argon2")
    assert admin.check_password(PASSWORD)


def test_registra_el_evento_sin_la_contrasena(consola, eventos):
    consola(PASSWORD, PASSWORD)
    call_command("crear_admin", "admin@ejemplo.com")

    accion, usuario, detalles = eventos[0]
    assert accion == "admin_creado"
    assert usuario.email == "admin@ejemplo.com"
    assert PASSWORD not in str(detalles)


def test_normaliza_el_telefono(consola, eventos):
    consola(PASSWORD, PASSWORD)
    call_command("crear_admin", "admin@ejemplo.com", "--telefono", "443 123 4567")

    assert Usuario.objects.get(email="admin@ejemplo.com").telefono == "+524431234567"


def test_rechaza_correo_existente_sin_importar_mayusculas(consola, eventos):
    UsuarioFactory(email="admin@ejemplo.com")
    with pytest.raises(CommandError, match="Ya existe una cuenta con el correo"):
        call_command("crear_admin", "ADMIN@ejemplo.com")


def test_rechaza_correo_invalido(consola, eventos):
    with pytest.raises(CommandError, match="no tiene un formato válido"):
        call_command("crear_admin", "hola")

    assert not Usuario.objects.filter(email="hola").exists()


def test_rechaza_telefono_existente(consola, eventos):
    UsuarioFactory(telefono="+524431234567")
    with pytest.raises(CommandError, match="Ya existe una cuenta con el teléfono"):
        call_command("crear_admin", "nuevo@ejemplo.com", "--telefono", "4431234567")


def test_rechaza_telefono_invalido(consola, eventos):
    with pytest.raises(CommandError):
        call_command("crear_admin", "nuevo@ejemplo.com", "--telefono", "123")


def test_vuelve_a_pedir_si_no_coinciden(consola, eventos):
    consola(PASSWORD, "Otra12345", PASSWORD, PASSWORD)
    call_command("crear_admin", "admin@ejemplo.com")

    assert Usuario.objects.filter(email="admin@ejemplo.com").exists()


def test_rechaza_contrasena_debil_tres_veces(consola, eventos):
    """La contraseña debe cumplir la política de T-12 (mayúscula y número)."""
    consola(*(["sinmayuscula1", "sinmayuscula1"] * 3))
    with pytest.raises(CommandError, match="Demasiados intentos"):
        call_command("crear_admin", "admin@ejemplo.com")

    assert not Usuario.objects.filter(email="admin@ejemplo.com").exists()
    assert eventos == []