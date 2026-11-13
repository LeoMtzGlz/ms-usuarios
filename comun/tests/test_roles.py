import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from comun.roles import Rol
from usuarios.models import Usuario

"""
USR-121 test(roles): valida contrato, defecto y restricción en BD
"""

def test_valores_del_contrato():
    assert Rol.values == ["administrador", "cliente", "operativo"]
    assert Rol.ADMINISTRADOR.label == "Administrador"


@pytest.mark.django_db
def test_rol_por_defecto_es_cliente():
    u = Usuario.objects.create_user(
        email="ana@example.com", telefono="+523531234567", password="Segura123"
    )  # AJUSTAR: campos obligatorios reales de create_user
    assert u.rol == Rol.CLIENTE


@pytest.mark.django_db
def test_superusuario_es_administrador():
    u = Usuario.objects.create_superuser(
        email="admin@example.com", telefono="+523531234568", password="Segura123"
    )
    assert u.rol == Rol.ADMINISTRADOR


@pytest.mark.django_db
def test_full_clean_rechaza_rol_inventado():
    u = Usuario(email="x@example.com", telefono="+523531234569", rol="superjefe")
    with pytest.raises(ValidationError) as e:
        u.full_clean()
    assert "rol" in e.value.message_dict


@pytest.mark.django_db
def test_postgresql_rechaza_rol_inventado():
    u = Usuario.objects.create_user(
        email="y@example.com", telefono="+523531234570", password="Segura123"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.filter(pk=u.pk).update(rol="superjefe")