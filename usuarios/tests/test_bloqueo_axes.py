"""ST-185: pruebas de bloqueo de inicio de sesión con Django Axes."""

from datetime import timedelta

import pytest
from axes.models import AccessAttempt
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from usuarios.tests.factories import PASSWORD_PRUEBA

pytestmark = pytest.mark.django_db


# El sexto intento debe bloquear incluso con la contraseña correcta.
def test_sexto_intento_con_password_correcta_sigue_bloqueado(usuario, llaves, axes_habilitado):
    anonimo = APIClient()

    for _ in range(settings.AXES_FAILURE_LIMIT):
        anonimo.post(
            "/api/v1/auth/login/",
            {"email": usuario.email, "password": "incorrecta"},
            format="json",
        )

    respuesta = anonimo.post(
        "/api/v1/auth/login/",
        {"email": usuario.email, "password": PASSWORD_PRUEBA},
        format="json",
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "cuenta_bloqueada"


# Al terminar el enfriamiento de 15 minutos, el usuario puede iniciar sesión.
def test_puede_iniciar_sesion_despues_del_enfriamiento(usuario, llaves, axes_habilitado):
    anonimo = APIClient()

    for _ in range(settings.AXES_FAILURE_LIMIT):
        anonimo.post(
            "/api/v1/auth/login/",
            {"email": usuario.email, "password": "incorrecta"},
            format="json",
        )

    bloqueada = anonimo.post(
        "/api/v1/auth/login/",
        {"email": usuario.email, "password": PASSWORD_PRUEBA},
        format="json",
    )
    assert bloqueada.status_code == 403

    AccessAttempt.objects.filter(
        username__iexact=usuario.email
    ).update(
        attempt_time=timezone.now() - settings.AXES_COOLOFF_TIME - timedelta(minutes=1)
    )

    respuesta = anonimo.post(
        "/api/v1/auth/login/",
        {"email": usuario.email, "password": PASSWORD_PRUEBA},
        format="json",
    )

    assert respuesta.status_code == 200
    assert "access" in respuesta.json()
    assert "refresh" in respuesta.json()