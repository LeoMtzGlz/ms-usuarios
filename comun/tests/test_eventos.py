import json
import logging

import pytest

from comun.eventos import registrar_evento
from usuarios.models import Estado
from usuarios.tests.factories import UsuarioFactory


def _eventos(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == "svc.auditoria"]


@pytest.mark.django_db
def test_registrar_evento_oculta_datos_sensibles(caplog):
    caplog.set_level(logging.INFO, logger="svc.auditoria")
    usuario = UsuarioFactory()
    registrar_evento("login", usuario, password="Secreta123", codigo="123456", ip_cliente="1.2.3.4")
    evento = _eventos(caplog)[-1]
    assert evento["accion"] == "login"
    assert evento["usuario_id"] == str(usuario.pk)
    assert evento["detalles"]["password"] == "***"
    assert evento["detalles"]["codigo"] == "***"
    assert "Secreta123" not in caplog.text and "123456" not in caplog.text


@pytest.mark.django_db
def test_cambiar_estado_registra_el_evento(caplog):
    caplog.set_level(logging.INFO, logger="svc.auditoria")
    usuario = UsuarioFactory()
    usuario.cambiar_estado(Estado.INACTIVO)
    evento = _eventos(caplog)[-1]
    assert evento["accion"] == "estado_cambiado"
    assert evento["detalles"]["anterior"] == "activo"
    assert evento["detalles"]["nuevo"] == "inactivo"
