"""Pruebas de t-22/st-169 (HU-22): los registros de acceso de más de 90 días se borran.

Casos P21-P26 del plan de pruebas de la ST-170 (Isis).
``fecha`` usa auto_now_add, así que las fechas viejas se fabrican con ``.update(fecha=...)``.
"""
from datetime import timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from notificaciones.models import Notificacion
from usuarios.limpieza import CADA_CUANTO, limpiar_accesos_viejos, limpiar_si_toca
from usuarios.models import ControlLimpieza, RegistroAcceso, Usuario
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

AHORA = timezone.now()


def _acceso(usuario, dias_atras, ahora=None):
    ahora = ahora or AHORA
    acceso = RegistroAcceso.objects.create(
        usuario=usuario, ip="200.1.2.3", dispositivo="Chrome 131 en Windows 10", exitoso=True
    )
    RegistroAcceso.objects.filter(pk=acceso.pk).update(fecha=ahora - timedelta(days=dias_atras))
    return acceso


@pytest.fixture
def usuario_con_accesos():
    usuario = UsuarioFactory()
    accesos = {dias: _acceso(usuario, dias) for dias in (1, 89, 91, 200)}
    return usuario, accesos


def _quedan():
    return set(RegistroAcceso.objects.values_list("id", flat=True))


# P21: 89, 90 y 91 días -> solo se borra lo de más de 90
def test_borra_solo_los_de_mas_de_90_dias(usuario_con_accesos):
    _, accesos = usuario_con_accesos
    limpiar_accesos_viejos(ahora=AHORA)
    assert _quedan() == {accesos[1].id, accesos[89].id}


def test_el_de_90_dias_exactos_se_queda():
    # Se borra lo que tiene MÁS de 90 días: fecha == límite se queda.
    exacto = _acceso(UsuarioFactory(), 90)
    limpiar_accesos_viejos(ahora=AHORA)
    assert RegistroAcceso.objects.filter(pk=exacto.pk).exists()


# P22: devuelve cuántos borró
def test_devuelve_cuantos_borro(usuario_con_accesos):
    assert limpiar_accesos_viejos(ahora=AHORA) == 2  # 91 y 200
    assert limpiar_accesos_viejos(ahora=AHORA) == 0  # ya no queda nada viejo


def test_borra_por_lotes(usuario_con_accesos):
    usuario, _ = usuario_con_accesos
    for _ in range(5):
        _acceso(usuario, 100)
    assert limpiar_accesos_viejos(ahora=AHORA, tamano_lote=2) == 7
    assert RegistroAcceso.objects.count() == 2


def test_borra_de_todos_los_usuarios(usuario_con_accesos):
    otro = UsuarioFactory()
    _acceso(otro, 120)
    reciente = _acceso(otro, 5)
    limpiar_accesos_viejos(ahora=AHORA)
    assert list(otro.accesos.values_list("id", flat=True)) == [reciente.id]


def test_dias_invalidos():
    with pytest.raises(ValueError):
        limpiar_accesos_viejos(dias=0)


# P23: el comando respeta --dias
def test_comando_por_defecto_90(usuario_con_accesos, capsys):
    call_command("limpiar_accesos")
    assert "2 registros de acceso borrados (más de 90 días)" in capsys.readouterr().out


def test_comando_con_dias_30(usuario_con_accesos, capsys):
    _, accesos = usuario_con_accesos
    call_command("limpiar_accesos", "--dias", "30")
    assert _quedan() == {accesos[1].id}
    assert "3 registros de acceso borrados (más de 30 días)" in capsys.readouterr().out


def test_comando_con_dias_cero_da_error():
    with pytest.raises(CommandError):
        call_command("limpiar_accesos", "--dias", "0")


# P24: dos veces el mismo día -> solo limpia la primera
def test_la_segunda_vez_el_mismo_dia_no_limpia(usuario_con_accesos):
    usuario, _ = usuario_con_accesos
    assert limpiar_si_toca(ahora=AHORA) == 2
    _acceso(usuario, 95)  # aparece otro viejo después de la primera limpieza
    assert limpiar_si_toca(ahora=AHORA + timedelta(hours=23)) is None
    assert RegistroAcceso.objects.count() == 3


# P25: pasadas 24 h vuelve a limpiar
def test_pasadas_24_horas_vuelve_a_limpiar(usuario_con_accesos):
    usuario, _ = usuario_con_accesos
    limpiar_si_toca(ahora=AHORA)
    nuevo_viejo = _acceso(usuario, 95)
    assert limpiar_si_toca(ahora=AHORA + CADA_CUANTO) is not None
    assert not RegistroAcceso.objects.filter(pk=nuevo_viejo.pk).exists()


def test_guarda_la_hora_de_la_ultima_limpieza():
    limpiar_si_toca(ahora=AHORA)
    control = ControlLimpieza.objects.get(nombre="limpiar_accesos")
    assert control.ultima_ejecucion == AHORA


# P26: no toca otras tablas
def test_no_toca_usuarios_ni_notificaciones(usuario_con_accesos):
    usuario, _ = usuario_con_accesos
    Notificacion.objects.create(destinatario=usuario, canal="email", plantilla="bienvenida")
    usuarios_antes = Usuario.objects.count()
    limpiar_accesos_viejos(ahora=AHORA)
    assert Usuario.objects.count() == usuarios_antes
    assert Notificacion.objects.count() == 1


# El worker la llama en cada ciclo
def test_el_worker_limpia_los_accesos_viejos(usuario_con_accesos, monkeypatch):
    monkeypatch.setattr("notificaciones.worker.cargar_resolver", lambda: lambda canal: None)
    _, accesos = usuario_con_accesos
    call_command("procesar_notificaciones", "--una-vez")
    assert _quedan() == {accesos[1].id, accesos[89].id}


def test_si_la_limpieza_falla_el_worker_sigue(monkeypatch, caplog):
    monkeypatch.setattr("notificaciones.worker.cargar_resolver", lambda: lambda canal: None)

    def falla(*args, **kwargs):
        raise RuntimeError("sin base")

    monkeypatch.setattr(
        "notificaciones.management.commands.procesar_notificaciones.limpiar_si_toca", falla
    )
    call_command("procesar_notificaciones", "--una-vez")  # no lanza error
    assert "No se pudo limpiar el historial de accesos" in caplog.text