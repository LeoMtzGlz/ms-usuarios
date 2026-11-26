import pytest
from django.core import mail
from django.test import override_settings

from notificaciones.canales import CanalCorreo
from notificaciones.plantillas import PLANTILLAS_CORREO, renderizar_plantilla_correo

PIE_OBLIGATORIO = "Correo automático, no respondas."


@pytest.mark.parametrize(
    "nombre_plantilla,contexto,texto_esperado",
    [
        ("activacion", {"nombre": "Daniel", "codigo": "987654"}, "987654"),
        ("bienvenida", {"nombre": "Daniel", "url_login": "https://app.ejemplo.com/login"}, "Daniel"),
        ("recuperacion_password", {"nombre": "Daniel", "codigo": "456123"}, "456123"),
        ("cambio_password", {"nombre": "Daniel", "fecha": "18/11/2026"}, "18/11/2026"),
        ("bloqueo_cuenta", {"nombre": "Daniel", "tiempo_bloqueo": "30 minutos"}, "30 minutos"),
        ("cuenta_creada", {"nombre": "Daniel", "correo": "daniel@ejemplo.com"}, "daniel@ejemplo.com"),
    ],
)
def test_renderizar_plantillas_con_pie_comun(nombre_plantilla, contexto, texto_esperado):
    asunto, texto_plano, html = renderizar_plantilla_correo(nombre_plantilla, contexto)

    assert asunto
    assert texto_esperado in html
    assert texto_esperado in texto_plano
    assert PIE_OBLIGATORIO in html
    assert PIE_OBLIGATORIO in texto_plano


def test_total_plantillas_es_seis():
    # 5 de t-08/st-42 + cuenta_creada de t-15/st-142
    assert len(PLANTILLAS_CORREO) == 6


def test_plantilla_desconocida_lanza_error():
    with pytest.raises(ValueError, match="Plantilla de correo desconocida"):
        renderizar_plantilla_correo("plantilla_inexistente", {})


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@ejemplo.com",
)
def test_canal_correo_envia_html_multiparte():
    asunto, texto_plano, html = renderizar_plantilla_correo(
        "activacion", {"nombre": "Daniel", "codigo": "112233"}
    )

    canal = CanalCorreo()
    canal.enviar(destino="daniel@ejemplo.com", asunto=asunto, texto=texto_plano, html=html)

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.subject == "Activa tu cuenta"
    assert "112233" in correo.body
    assert PIE_OBLIGATORIO in correo.body
    assert len(correo.alternatives) == 1
    contenido_html, mimetype = correo.alternatives[0]
    assert mimetype == "text/html"
    assert "112233" in contenido_html
    assert PIE_OBLIGATORIO in contenido_html