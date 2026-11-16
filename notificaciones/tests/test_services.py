import pytest
from django.contrib.auth import get_user_model
from notificaciones.services import notificar
from notificaciones.models import Notificacion

Usuario = get_user_model()


@pytest.mark.django_db
def test_notificar_guarda_en_bandeja():
    usuario = Usuario.objects.create_user(email="katia_test@ejemplo.com", password="Password123")

    noti = notificar(
        usuario=usuario,
        plantilla="codigo_activacion",
        contexto={"codigo": "654321"},
        canal="correo"
    )

    assert noti.destinatario == usuario
    assert noti.canal == "correo"
    assert noti.estado == Notificacion.ESTADO_PENDIENTE