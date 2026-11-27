"""Pruebas de HU-07/ST-91: limpieza de tokens JWT vencidos, una vez al día desde el worker."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.limpieza import CADA_CUANTO, NOMBRE_TAREA_TOKENS, limpiar_tokens_si_toca
from usuarios.models import ControlLimpieza

pytestmark = pytest.mark.django_db


def _token_vencido(usuario):
    """Crea un refresh token y lo marca como vencido hace un día."""
    registro = OutstandingToken.objects.get(jti=RefreshToken.for_user(usuario)["jti"])
    registro.expires_at = timezone.now() - timedelta(days=1)
    registro.save(update_fields=["expires_at"])
    return registro


def test_limpieza_elimina_tokens_vencidos_y_conserva_vigentes(llaves, usuario):
    registro_vencido = _token_vencido(usuario)
    registro_vigente = OutstandingToken.objects.get(jti=RefreshToken.for_user(usuario)["jti"])
    BlacklistedToken.objects.create(token=registro_vencido)
    BlacklistedToken.objects.create(token=registro_vigente)

    call_command("flushexpiredtokens")

    assert not OutstandingToken.objects.filter(pk=registro_vencido.pk).exists()
    assert not BlacklistedToken.objects.filter(token_id=registro_vencido.pk).exists()
    assert OutstandingToken.objects.filter(pk=registro_vigente.pk).exists()
    assert BlacklistedToken.objects.filter(token_id=registro_vigente.pk).exists()


def test_solo_limpia_una_vez_al_dia(llaves, usuario):
    ahora = timezone.now()
    assert limpiar_tokens_si_toca(ahora=ahora) is True

    registro = _token_vencido(usuario)
    assert limpiar_tokens_si_toca(ahora=ahora + timedelta(hours=1)) is False
    assert OutstandingToken.objects.filter(pk=registro.pk).exists()


def test_pasadas_24_horas_vuelve_a_limpiar(llaves, usuario):
    ahora = timezone.now()
    limpiar_tokens_si_toca(ahora=ahora)
    registro = _token_vencido(usuario)

    assert limpiar_tokens_si_toca(ahora=ahora + CADA_CUANTO) is True
    assert not OutstandingToken.objects.filter(pk=registro.pk).exists()
    control = ControlLimpieza.objects.get(nombre=NOMBRE_TAREA_TOKENS)
    assert control.ultima_ejecucion == ahora + CADA_CUANTO


def test_el_worker_limpia_los_tokens_vencidos(llaves, usuario, monkeypatch):
    monkeypatch.setattr("notificaciones.worker.cargar_resolver", lambda: lambda canal: None)
    registro = _token_vencido(usuario)

    call_command("procesar_notificaciones", "--una-vez")

    assert not OutstandingToken.objects.filter(pk=registro.pk).exists()


def test_si_la_limpieza_de_tokens_falla_el_worker_sigue(monkeypatch, caplog):
    monkeypatch.setattr("notificaciones.worker.cargar_resolver", lambda: lambda canal: None)

    def falla(*args, **kwargs):
        raise RuntimeError("base de datos caída")

    monkeypatch.setattr(
        "notificaciones.management.commands.procesar_notificaciones.limpiar_tokens_si_toca", falla
    )
    call_command("procesar_notificaciones", "--una-vez")  # no lanza error

    assert "No se pudo limpiar los tokens vencidos" in caplog.text
