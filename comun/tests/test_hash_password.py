import pytest
from django.contrib.auth.hashers import make_password
from django.db import connection

from usuarios.models import Usuario
from usuarios.tests.factories import UsuarioFactory  # AJUSTAR: ruta real

PASSWORD = "Segura123"
HASHERS_REALES = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]


@pytest.fixture(autouse=True)
def hashers_reales(settings):
    settings.PASSWORD_HASHERS = HASHERS_REALES


@pytest.fixture
def usuario_con_password(db):
    usuario = UsuarioFactory()
    usuario.set_password(PASSWORD)
    usuario.save()
    return usuario


def test_set_password_guarda_argon2(usuario_con_password):
    usuario_con_password.refresh_from_db()
    assert usuario_con_password.password.startswith("argon2")
    assert PASSWORD not in usuario_con_password.password
    assert usuario_con_password.check_password(PASSWORD)


def test_create_user_guarda_argon2(db):
    usuario = Usuario.objects.create_user(
        email="ana@example.com", telefono="+523531234567", password=PASSWORD
    )  # AJUSTAR: campos obligatorios reales de create_user
    usuario.refresh_from_db()
    assert usuario.password.startswith("argon2")


def test_valor_real_en_postgresql(usuario_con_password):
    """Lee la columna directo de la BD, sin pasar por el ORM."""
    tabla = Usuario._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT password FROM {tabla} WHERE id = %s", [usuario_con_password.pk])
        (guardado,) = cursor.fetchone()
    assert guardado.startswith("argon2$argon2id$")
    assert PASSWORD not in guardado


def test_hash_pbkdf2_antiguo_funciona_y_se_actualiza(usuario_con_password):
    """PBKDF2 es respaldo: una contraseña vieja sigue sirviendo y se re-hashea a Argon2."""
    usuario_con_password.password = make_password(PASSWORD, hasher="pbkdf2_sha256")
    usuario_con_password.save(update_fields=["password"])

    assert usuario_con_password.check_password(PASSWORD)
    usuario_con_password.refresh_from_db()
    assert usuario_con_password.password.startswith("argon2")