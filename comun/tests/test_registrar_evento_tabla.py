import json
import logging

import pytest
from django.test import RequestFactory

from comun.eventos import registrar_evento
from comun.models import EventoAuditoria
from usuarios.models import Usuario
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _request(**extra):
    return RequestFactory().get("/", **extra)


def test_crea_la_fila():
    usuario = UsuarioFactory()
    request = _request(REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="Mozilla/5.0")
    registrar_evento("login", usuario, request, resultado="error", motivo="x")
    fila = EventoAuditoria.objects.get()
    assert fila.usuario == usuario
    assert fila.accion == "login"
    assert fila.resultado == "error"
    assert fila.ip == "10.0.0.5"
    assert fila.user_agent == "Mozilla/5.0"
    assert fila.detalles == {"motivo": "x"}


def test_sin_request_ni_usuario():
    registrar_evento("admin_creado")
    fila = EventoAuditoria.objects.get()
    assert fila.usuario is None
    assert fila.ip is None
    assert fila.user_agent == ""


def test_enmascara_claves_sensibles():
    registrar_evento("x", password="Secreta123", codigo="123456")
    fila = EventoAuditoria.objects.get()
    assert fila.detalles["password"] == "***"
    assert fila.detalles["codigo"] == "***"
    assert "Secreta123" not in str(fila.detalles)


def test_enmascara_anidados():
    registrar_evento("x", datos={"password": "Secreta123"}, lista=[{"token": "abc"}])
    assert EventoAuditoria.objects.get().detalles == {
        "datos": {"password": "***"},
        "lista": [{"token": "***"}],
    }


def test_ip_invalida_se_guarda_como_none():
    registrar_evento("x", request=_request(REMOTE_ADDR="no-es-ip"))
    assert EventoAuditoria.objects.get().ip is None


def test_si_falla_el_guardado_no_rompe_al_llamador(caplog):
    caplog.set_level(logging.ERROR, logger="svc.auditoria")
    registrar_evento("x", cosa={1, 2})
    assert EventoAuditoria.objects.count() == 0
    assert any(r.name == "svc.auditoria" and r.levelno == logging.ERROR for r in caplog.records)
    assert Usuario.objects.count() == 0


def test_sigue_escribiendo_al_log(caplog):
    caplog.set_level(logging.INFO, logger="svc.auditoria")
    registrar_evento("login", motivo="x")
    evento = json.loads(caplog.records[-1].message)
    assert evento["accion"] == "login"
    assert evento["detalles"] == {"motivo": "x"}
