"""t-10/st-51: cada notificación sale por su propio canal (comentario del PR #53)."""
import pytest
from django.core import mail
from django.test import override_settings

from notificaciones import worker
from notificaciones.canales import CanalConsola, CanalCorreo
from notificaciones.models import Notificacion
from notificaciones.services import obtener_canal

PLANTILLAS_PRUEBA = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "OPTIONS": {
        "loaders": [("django.template.loaders.locmem.Loader", {
            "notificaciones/prueba.txt": "Tu código es {{ codigo }}",
        })],
    },
}]


@override_settings(CANAL_NOTIFICACIONES="consola")
def test_en_desarrollo_todo_sale_por_consola():
    assert isinstance(obtener_canal("correo"), CanalConsola)
    assert isinstance(obtener_canal("whatsapp"), CanalConsola)


@override_settings(CANAL_NOTIFICACIONES="correo")
def test_usa_el_canal_que_recibe():
    assert isinstance(obtener_canal("correo"), CanalCorreo)
    assert isinstance(obtener_canal("consola"), CanalConsola)


@override_settings(CANAL_NOTIFICACIONES="correo")
def test_sin_argumento_usa_el_setting():
    assert isinstance(obtener_canal(), CanalCorreo)


@override_settings(CANAL_NOTIFICACIONES="correo")
def test_canal_sin_clase_lanza_error():
    with pytest.raises(ValueError, match="whatsapp"):
        obtener_canal("whatsapp")


@pytest.mark.django_db
@override_settings(
    CANAL_NOTIFICACIONES="correo",
    TEMPLATES=PLANTILLAS_PRUEBA,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@ejemplo.com",
)
def test_worker_manda_cada_notificacion_por_su_canal(usuario):
    datos = {"plantilla": "prueba", "contexto": {"codigo": "123456"}}
    por_correo = Notificacion.objects.create(destinatario=usuario, canal="correo", **datos)
    por_whatsapp = Notificacion.objects.create(destinatario=usuario, canal="whatsapp", **datos)

    resultado = worker.procesar_lote()

    por_correo.refresh_from_db()
    por_whatsapp.refresh_from_db()
    assert resultado.enviadas == 1
    assert resultado.fallidas == 1
    assert por_correo.estado == Notificacion.ESTADO_ENVIADA
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario.email]
    # WhatsApp aún no tiene clase (T-09): falla y queda pendiente para reintento (ST-52);
    # tras 3 ciclos sale por correo con la copia de respaldo.
    assert por_whatsapp.estado == Notificacion.ESTADO_PENDIENTE
    assert "No hay canal disponible para: whatsapp" in por_whatsapp.error
