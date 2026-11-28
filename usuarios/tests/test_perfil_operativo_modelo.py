from datetime import time

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from comun.roles import Rol
from usuarios.models import PerfilOperativo, Usuario


def _crear_usuario(email: str, rol: str = Rol.OPERATIVO) -> Usuario:
    return Usuario.objects.create_user(email=email, password="Password123!", rol=rol)


@pytest.mark.django_db
def test_placas_duplicadas_sin_distinguir_mayusculas_falla():
    op1 = _crear_usuario("op1@ejemplo.com", Rol.OPERATIVO)
    op2 = _crear_usuario("op2@ejemplo.com", Rol.OPERATIVO)

    PerfilOperativo.objects.create(usuario=op1, placas="abc123")

    with pytest.raises((ValidationError, IntegrityError)):
        with transaction.atomic():
            PerfilOperativo.objects.create(usuario=op2, placas="ABC123")


@pytest.mark.django_db
def test_no_permite_perfil_operativo_a_rol_no_operativo():
    cliente = _crear_usuario("cliente@ejemplo.com", Rol.CLIENTE)

    with pytest.raises(ValidationError) as exc:
        PerfilOperativo.objects.create(usuario=cliente, vehiculo="Moto")

    assert "usuario" in exc.value.message_dict


@pytest.mark.django_db
def test_horario_debe_tener_hora_inicio_y_hora_fin_juntas():
    op = _crear_usuario("op3@ejemplo.com", Rol.OPERATIVO)

    with pytest.raises((ValidationError, IntegrityError)):
        with transaction.atomic():
            PerfilOperativo.objects.create(usuario=op, hora_inicio=time(8, 0))


@pytest.mark.django_db
def test_creacion_valida_y_placas_vacias_permitidas():
    op1 = _crear_usuario("op4@ejemplo.com", Rol.OPERATIVO)
    op2 = _crear_usuario("op5@ejemplo.com", Rol.OPERATIVO)

    p1 = PerfilOperativo.objects.create(
        usuario=op1,
        vehiculo="Nissan NP300",
        placas="",
        ruta="Centro",
        hora_inicio=time(8, 0),
        hora_fin=time(16, 0),
    )
    p2 = PerfilOperativo.objects.create(usuario=op2, placas=None)

    assert p1.placas is None
    assert p2.placas is None
    