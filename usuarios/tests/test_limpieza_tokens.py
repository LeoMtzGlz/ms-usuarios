
"""Pruebas de HU-07/ST-91: limpieza de tokens JWT vencidos."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken


pytestmark = pytest.mark.django_db


def test_limpieza_elimina_tokens_vencidos_y_conserva_vigentes(llaves, usuario):
    vencido = RefreshToken.for_user(usuario)
    vigente = RefreshToken.for_user(usuario)

    registro_vencido = OutstandingToken.objects.get(jti=vencido["jti"])
    registro_vigente = OutstandingToken.objects.get(jti=vigente["jti"])

    BlacklistedToken.objects.create(token=registro_vencido)
    BlacklistedToken.objects.create(token=registro_vigente)

    registro_vencido.expires_at = timezone.now() - timedelta(days=1)
    registro_vencido.save(update_fields=["expires_at"])

    call_command("flushexpiredtokens")

    assert not OutstandingToken.objects.filter(
        pk=registro_vencido.pk
    ).exists()

    assert not BlacklistedToken.objects.filter(
        token_id=registro_vencido.pk
    ).exists()

    assert OutstandingToken.objects.filter(
        pk=registro_vigente.pk
    ).exists()

    assert BlacklistedToken.objects.filter(
        token_id=registro_vigente.pk
    ).exists()
