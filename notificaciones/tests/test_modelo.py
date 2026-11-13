import pytest
from django.contrib.auth import get_user_model
from notificaciones.models import Notificacion

Usuario = get_user_model()


@pytest.mark.django_db
def test_crear_notificacion_pendiente():
    # 1. Creamos un usuario de prueba
    usuario = Usuario.objects.create_user(
        email="prueba@ejemplo.com",
        password="Password123",
    )

    # 2. Creamos la notificación
    noti = Notificacion.objects.create(
        destinatario=usuario,
        canal="correo",
        plantilla="codigo_activacion",
        contexto={"codigo": "123456"},
    )

    # 3. Comprobamos que se guardó bien y con los valores por defecto
    assert noti.estado == Notificacion.ESTADO_PENDIENTE
    assert noti.intentos == 0
    assert noti.error == ""
    assert noti.creado_en is not None
    assert noti.actualizado_en is not None