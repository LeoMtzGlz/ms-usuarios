import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings

from notificaciones.canales import CanalCorreo
from notificaciones.models import CanalNotificacion, Notificacion
from notificaciones.services import (
    notificar,
    obtener_canal,
    preparar_contenido_notificacion,
)
from usuarios.models import Usuario


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@svc-usuarios.com",
    CANAL_NOTIFICACIONES="correo",
)
def test_flujo_completo_notificacion_correo_en_outbox():
    """Verifica el ciclo completo: notificar -> preparar_contenido -> CanalCorreo -> mail.outbox."""
    usuario = Usuario.objects.create_user(
        email="daniel.prueba@ejemplo.com",
        password="Password123!",
    )

    notificacion = notificar(
        usuario=usuario,
        plantilla="activacion",
        contexto={"nombre": "Daniel", "codigo": "739104"},
        canal=CanalNotificacion.CORREO,
    )

    asunto, texto, html = preparar_contenido_notificacion(notificacion)
    canal = obtener_canal(notificacion.canal)
    canal.enviar(
        destino=usuario.email,
        asunto=asunto,
        texto=texto,
        html=html,
    )

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]

    assert correo.to == ["daniel.prueba@ejemplo.com"]
    assert correo.from_email == "notificaciones@svc-usuarios.com"
    assert correo.subject == "Activa tu cuenta"
    assert "739104" in correo.body
    assert "Correo automático, no respondas." in correo.body

    # Verificar versión alternativa HTML multiparte
    assert len(correo.alternatives) == 1
    contenido_html, mimetype = correo.alternatives[0]
    assert mimetype == "text/html"
    assert "739104" in contenido_html
    assert "Correo automático, no respondas." in contenido_html


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@svc-usuarios.com",
    CANAL_NOTIFICACIONES="correo",
)
@pytest.mark.parametrize(
    "plantilla,contexto,dato_clave",
    [
        ("activacion", {"nombre": "Daniel", "codigo": "111222"}, "111222"),
        ("bienvenida", {"nombre": "Daniel", "url_login": "https://app.local/login"}, "Daniel"),
        ("recuperacion_password", {"nombre": "Daniel", "codigo": "333444"}, "333444"),
        ("cambio_password", {"nombre": "Daniel", "fecha": "23/11/2026"}, "23/11/2026"),
        ("bloqueo_cuenta", {"nombre": "Daniel", "tiempo_bloqueo": "15 minutos"}, "15 minutos"),
    ],
)
def test_todas_las_plantillas_llegan_a_mail_outbox(plantilla, contexto, dato_clave):
    """Comprueba que las 5 plantillas se despachen correctamente hacia mail.outbox."""
    noti = Notificacion(
        canal=CanalNotificacion.CORREO,
        plantilla=plantilla,
        contexto=contexto,
    )
    asunto, texto, html = preparar_contenido_notificacion(noti)

    canal = CanalCorreo()
    canal.enviar(destino="destino@ejemplo.com", asunto=asunto, texto=texto, html=html)

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert dato_clave in correo.body
    assert "Correo automático, no respondas." in correo.body
    assert correo.alternatives[0][1] == "text/html"
    assert dato_clave in correo.alternatives[0][0]


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@svc-usuarios.com",
)
def test_comando_sendtestemail_usa_outbox():
    """Valida que el comando administrativo sendtestemail genere el correo de prueba."""
    call_command("sendtestemail", "cuenta_proyecto@ejemplo.com")

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == ["cuenta_proyecto@ejemplo.com"]
    assert "Test email" in correo.subject