"""Pruebas del modelo EventoAuditoria (hu-26/st-187)."""
from datetime import timedelta

import pytest
from django.db import connection

from comun.models import EventoAuditoria, ResultadoEvento
from usuarios.tests.factories import UsuarioFactory

TABLA = EventoAuditoria._meta.db_table


@pytest.mark.django_db
def test_evento_minimo_usa_los_valores_por_defecto():
    evento = EventoAuditoria.objects.create(accion="login_fallido")
    evento.refresh_from_db()
    assert evento.usuario is None
    assert evento.resultado == ResultadoEvento.OK
    assert evento.ip is None
    assert evento.user_agent == ""
    assert evento.detalles == {}
    assert evento.fecha is not None


def test_detalles_por_defecto_no_se_comparten_entre_eventos():
    uno, otro = EventoAuditoria(accion="a"), EventoAuditoria(accion="b")
    uno.detalles["clave"] = "valor"
    assert otro.detalles == {}


def test_evento_sin_guardar_se_muestra_sin_fecha():
    assert str(EventoAuditoria(accion="logout")) == "logout (ok)"


@pytest.mark.django_db
def test_guarda_todos_los_campos(usuario):
    evento = EventoAuditoria.objects.create(
        usuario=usuario,
        accion="rol_cambiado",
        resultado=ResultadoEvento.ERROR,
        ip="2001:db8::1",
        user_agent="Mozilla/5.0 (Windows NT 10.0)",
        detalles={"anterior": "operador", "nuevo": "administrador", "intentos": [1, 2]},
    )
    evento.refresh_from_db()
    assert evento.usuario == usuario
    assert evento.resultado == "error"
    assert evento.ip == "2001:db8::1"
    assert evento.user_agent == "Mozilla/5.0 (Windows NT 10.0)"
    assert evento.detalles == {"anterior": "operador", "nuevo": "administrador", "intentos": [1, 2]}
    assert list(usuario.eventos_auditoria.all()) == [evento]
    assert str(evento).startswith("rol_cambiado (error) ")


@pytest.mark.django_db
def test_detalles_es_jsonb_y_se_puede_filtrar_por_sus_claves():
    EventoAuditoria.objects.create(accion="envio_fallido", detalles={"canal": "whatsapp"})
    EventoAuditoria.objects.create(accion="envio_fallido", detalles={"canal": "correo"})
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT data_type FROM information_schema.columns WHERE table_name = %s AND column_name = 'detalles'",
            [TABLA],
        )
        assert cursor.fetchone()[0] == "jsonb"
    assert EventoAuditoria.objects.filter(detalles__canal="whatsapp").count() == 1


@pytest.mark.django_db
def test_detalles_acepta_uuid_y_fechas(usuario):
    vence = usuario.date_joined + timedelta(minutes=10)
    evento = EventoAuditoria.objects.create(accion="registro", detalles={"id": usuario.pk, "vence": vence})
    evento.refresh_from_db()
    assert evento.detalles["id"] == str(usuario.pk)
    assert evento.detalles["vence"].startswith(vence.date().isoformat())


@pytest.mark.django_db
def test_hay_indice_por_fecha():
    with connection.cursor() as cursor:
        restricciones = connection.introspection.get_constraints(cursor, TABLA)
    indices = [r["columns"] for r in restricciones.values() if r["index"] and not r["primary_key"]]
    assert ["fecha"] in indices
    assert ["accion", "fecha"] in indices


@pytest.mark.django_db
def test_borrar_al_usuario_conserva_su_historial():
    usuario = UsuarioFactory()
    evento = EventoAuditoria.objects.create(usuario=usuario, accion="logout")
    usuario.delete()
    evento.refresh_from_db()
    assert evento.usuario is None
    assert evento.accion == "logout"


@pytest.mark.django_db
def test_el_mas_reciente_sale_primero_y_se_filtra_por_fechas():
    viejo = EventoAuditoria.objects.create(accion="login")
    nuevo = EventoAuditoria.objects.create(accion="logout")
    hace_una_semana = nuevo.fecha - timedelta(days=7)
    EventoAuditoria.objects.filter(pk=viejo.pk).update(fecha=hace_una_semana)
    assert list(EventoAuditoria.objects.all()) == [nuevo, viejo]
    ultimos_dias = EventoAuditoria.objects.filter(fecha__gte=hace_una_semana + timedelta(days=1))
    assert list(ultimos_dias) == [nuevo]
