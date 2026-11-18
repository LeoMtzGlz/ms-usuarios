import pytest
from django.contrib.auth import get_user_model
from usuarios.utils import generar_correo_institucional

Usuario = get_user_model()


@pytest.mark.django_db
def test_generar_correo_quita_acentos_y_minusculas():
    """Prueba que se quitan acentos y se pasa a minúsculas."""
    correo = generar_correo_institucional("José María", "Pérez")
    # El correo debe empezar con "josemariaperez" (sin acentos y en minúsculas)
    assert correo.startswith("josemariaperez")
    assert "@" in correo


@pytest.mark.django_db
def test_generar_correo_maneja_enie():
    """Prueba que la ñ se convierte correctamente."""
    correo = generar_correo_institucional("Peña", "Muñoz")
    # La ñ se convierte en 'n' por la normalización
    assert correo.startswith("penamunoz")


@pytest.mark.django_db
def test_generar_correo_evita_duplicados():
    """Prueba que si el correo existe, genera uno nuevo con diferentes números."""
    # 1. Creamos un usuario con un correo que sabemos que podría generarse
    # (Forzamos un correo falso para simular que ya existe)
    Usuario.objects.create_user(
        email="juanperez12@jiquilpan.tecnm.mx",
        password="Password123"
    )

    # 2. Intentamos generar el correo para el mismo nombre
    nuevo_correo = generar_correo_institucional("Juan", "Pérez")

    # 3. Como el 12 ya existe (o el que salga), la función debe generar otro número diferente
    # y no debe ser exactamente el mismo que ya existe.
    assert nuevo_correo != "juanperez12@jiquilpan.tecnm.mx"