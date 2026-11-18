import pytest
from django.core import mail
from django.test import override_settings
from notificaciones.canales import CanalCorreo
from notificaciones.services import obtener_canal



@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@ejemplo.com",
)
def test_canal_correo_envia_mensaje():

    canal = CanalCorreo()

    canal.enviar(
        destino="usuario@ejemplo.com",
        asunto="Código de activación",
        texto="Tu código de activación es 123456.",
    )

    # Comprobamos que se generó un correo
    assert len(mail.outbox) == 1

    correo = mail.outbox[0]

    # Comprobamos los datos del correo
    assert correo.subject == "Código de activación"
    assert correo.body == "Tu código de activación es 123456."
    assert correo.from_email == "notificaciones@ejemplo.com"
    assert correo.to == ["usuario@ejemplo.com"]

@override_settings(CANAL_NOTIFICACIONES="correo")
def test_obtener_canal_devuelve_canal_correo():

    canal = obtener_canal()

    assert isinstance(canal, CanalCorreo)