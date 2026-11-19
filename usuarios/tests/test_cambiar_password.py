"""t-12 / st-117: al cambiar la contraseña, deja de ser temporal."""
import json

import pytest
from django.test import RequestFactory

from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

NUEVA = "Definitiva2026"


def eventos(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == "svc.auditoria"]


def test_marca_la_contrasena_como_definitiva():
    usuario = UsuarioFactory(debe_cambiar_password=True)
    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert usuario.debe_cambiar_password is False


def test_guarda_la_contrasena_nueva_con_hash():
    usuario = UsuarioFactory(debe_cambiar_password=True)
    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert usuario.check_password(NUEVA)
    assert usuario.password != NUEVA
    assert usuario.password.startswith("argon2")


def test_la_contrasena_temporal_deja_de_funcionar():
    usuario = UsuarioFactory(debe_cambiar_password=True)
    usuario.set_password("Temporal2026")
    usuario.save()

    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert not usuario.check_password("Temporal2026")


def test_cierra_las_sesiones_abiertas_con_la_contrasena_anterior():
    usuario = UsuarioFactory(debe_cambiar_password=True, token_version=3)
    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert usuario.token_version == 4


def test_si_no_era_temporal_sigue_como_definitiva():
    usuario = UsuarioFactory(debe_cambiar_password=False)
    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert usuario.debe_cambiar_password is False
    assert usuario.check_password(NUEVA)


def test_solo_guarda_los_campos_de_la_contrasena():
    """No pisa cambios que otra petición haya hecho en otros campos del usuario."""
    usuario = UsuarioFactory(debe_cambiar_password=True, first_name="Ana")
    type(usuario).objects.filter(pk=usuario.pk).update(first_name="Ana María")

    usuario.cambiar_password(NUEVA)
    usuario.refresh_from_db()

    assert usuario.first_name == "Ana María"
    assert usuario.debe_cambiar_password is False


def test_registra_el_evento_sin_la_contrasena(caplog):
    usuario = UsuarioFactory(debe_cambiar_password=True)
    request = RequestFactory().post("/", REMOTE_ADDR="10.0.0.7")

    with caplog.at_level("INFO", logger="svc.auditoria"):
        usuario.cambiar_password(NUEVA, request=request)

    evento = [e for e in eventos(caplog) if e["accion"] == "password_cambiado"][-1]
    assert evento["usuario_id"] == str(usuario.pk)
    assert evento["ip"] == "10.0.0.7"
    assert evento["detalles"] == {"era_temporal": True}
    assert NUEVA not in json.dumps(evento)