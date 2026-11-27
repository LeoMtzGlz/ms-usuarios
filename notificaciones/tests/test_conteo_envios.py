"""Pruebas de T-11/ST-56: conteo diario de notificaciones enviadas."""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from notificaciones.models import CanalNotificacion, Notificacion
from notificaciones.services import contar_envios_hoy
from usuarios.tests.factories import UsuarioFactory


pytestmark = pytest.mark.django_db


def crear_notificacion(usuario, canal, estado, fecha=None):
    """Crea una notificación con estado y fecha controlados."""
    notificacion = Notificacion.objects.create(
        destinatario=usuario,
        canal=canal,
        plantilla="prueba",
        contexto={},
        estado=estado,
    )

    if fecha is not None:
        Notificacion.objects.filter(pk=notificacion.pk).update(
            actualizado_en=fecha
        )

    return notificacion


def test_contar_envios_hoy_por_canal():
    """El conteo debe separar los envíos de correo y WhatsApp."""
    usuario = UsuarioFactory()

    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA
    )
    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA
    )
    crear_notificacion(
        usuario, CanalNotificacion.WHATSAPP, Notificacion.ESTADO_ENVIADA
    )

    assert contar_envios_hoy(CanalNotificacion.CORREO) == 2
    assert contar_envios_hoy(CanalNotificacion.WHATSAPP) == 1


def test_contar_envios_hoy_excluye_pendientes_y_fallidas():
    """Solo deben contarse las notificaciones enviadas."""
    usuario = UsuarioFactory()

    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA
    )
    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_PENDIENTE
    )
    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_FALLIDA
    )

    assert contar_envios_hoy(CanalNotificacion.CORREO) == 1


def test_contar_envios_hoy_excluye_dias_anteriores():
    """Los envíos anteriores al día actual no deben contarse."""
    usuario = UsuarioFactory()

    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA
    )
    crear_notificacion(
        usuario,
        CanalNotificacion.CORREO,
        Notificacion.ESTADO_ENVIADA,
        timezone.now() - timedelta(days=1),
    )

    assert contar_envios_hoy(CanalNotificacion.CORREO) == 1


def test_contar_envios_hoy_sin_registros():
    """Si no existen envíos del canal, debe devolver cero."""
    assert contar_envios_hoy(CanalNotificacion.CORREO) == 0
    assert contar_envios_hoy(CanalNotificacion.WHATSAPP) == 0


def test_contar_envios_hoy_respeta_zona_horaria():
    """El conteo utiliza el día local, no la fecha UTC."""
    with timezone.override("America/Mexico_City"):
        usuario = UsuarioFactory()
        hoy = timezone.localdate()
        ayer = hoy - timedelta(days=1)
        zona = timezone.get_current_timezone()

        # Enviado ayer a las 23:45, hora local.
        fecha_ayer = timezone.make_aware(
            datetime.combine(ayer, time(23, 45)),
            zona,
        )

        # Enviado hoy a las 00:15, hora local.
        fecha_hoy = timezone.make_aware(
            datetime.combine(hoy, time(0, 15)),
            zona,
        )

        crear_notificacion(
            usuario,
            CanalNotificacion.CORREO,
            Notificacion.ESTADO_ENVIADA,
            fecha_ayer,
        )

        crear_notificacion(
            usuario,
            CanalNotificacion.CORREO,
            Notificacion.ESTADO_ENVIADA,
            fecha_hoy,
        )

        assert contar_envios_hoy(CanalNotificacion.CORREO) == 1


def test_contar_envios_hoy_excluye_desde_medianoche_siguiente():
    """El límite superior del rango es exclusivo: la medianoche de mañana ya no es hoy."""
    usuario = UsuarioFactory()
    zona = timezone.get_current_timezone()
    hoy = timezone.localdate()

    ultimo_instante_de_hoy = timezone.make_aware(datetime.combine(hoy, time.max), zona)
    medianoche_de_manana = timezone.make_aware(
        datetime.combine(hoy + timedelta(days=1), time.min), zona
    )

    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA, ultimo_instante_de_hoy
    )
    crear_notificacion(
        usuario, CanalNotificacion.CORREO, Notificacion.ESTADO_ENVIADA, medianoche_de_manana
    )

    assert contar_envios_hoy(CanalNotificacion.CORREO) == 1
