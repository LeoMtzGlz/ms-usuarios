import pytest
from django.contrib.auth import get_user_model
from notificaciones.models import Notificacion
from notificaciones.services import notificar

from django.db import transaction

Usuario = get_user_model()


@pytest.mark.django_db
def test_notificar_guarda_en_bandeja():
    usuario = Usuario.objects.create_user(
        email="katia_test@ejemplo.com", password="Password123"
    )
    noti = notificar(
        usuario=usuario,
        plantilla="codigo_activacion",
        contexto={"codigo": "654321"},
        canal="correo",
    )
    assert noti.destinatario == usuario
    assert noti.canal == "correo"
    assert noti.estado == Notificacion.ESTADO_PENDIENTE


@pytest.mark.django_db
def test_notificar_usa_canal_preferido_si_no_se_envia():
    """Prueba solicitada por el profesor."""
    usuario = Usuario.objects.create_user(
        email="preferido@ejemplo.com",
        password="Password123",
        canal_preferido="whatsapp"
    )
    # No enviamos el parámetro 'canal'
    noti = notificar(
        usuario=usuario,
        plantilla="aviso",
        contexto={"mensaje": "Hola"}
    )
    assert noti.canal == "whatsapp"


@pytest.mark.django_db
def test_notificar_lanza_error_si_canal_es_invalido():
    """Validación solicitada por el profesor."""
    usuario = Usuario.objects.create_user(
        email="error@ejemplo.com", password="Password123"
    )
    with pytest.raises(ValueError, match="Canal desconocido: telegram"):
        notificar(
            usuario=usuario,
            plantilla="aviso",
            contexto={},
            canal="telegram"
        )


@pytest.mark.django_db
def test_notificar_no_guarda_si_transaccion_se_revierte():

    # 1. Creamos un usuario de prueba
    usuario = Usuario.objects.create_user(
        email="rollback@ejemplo.com",
        password="Password123",
    )

    # 2. Verificamos que inicialmente no tenga notificaciones
    assert Notificacion.objects.filter(
        destinatario=usuario
    ).count() == 0

    # 3. Iniciamos una transacción y forzamos su reversión
    with pytest.raises(RuntimeError, match="Forzar rollback"):
        with transaction.atomic():

            # Creamos una notificación dentro de la transacción
            notificar(
                usuario=usuario,
                plantilla="codigo_activacion",
                contexto={"codigo": "123456"},
                canal="correo",
            )

            # Comprobamos que existe dentro de la transacción
            assert Notificacion.objects.filter(
                destinatario=usuario
            ).count() == 1

            # Provocamos un error para revertir la transacción
            raise RuntimeError("Forzar rollback")

    # 4. Comprobamos que la notificación ya no esté guardada
    assert Notificacion.objects.filter(
        destinatario=usuario
    ).count() == 0