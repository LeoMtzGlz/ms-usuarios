"""t-10/st-52: reintentos (3 fallos en total), respaldo de WhatsApp a correo y código vencido."""
from datetime import timedelta

import pytest
from django.utils import timezone

from notificaciones import worker
from notificaciones.models import Notificacion
from notificaciones.tests.test_worker import (  # noqa: F401  (plantillas es fixture autouse)
    CanalFalso, crear, plantillas, resolver_con,
)

pytestmark = pytest.mark.django_db


def correr(canal, veces=1):
    for _ in range(veces):
        worker.procesar_lote(obtener_canal=resolver_con(canal))


def falla():
    return CanalFalso(falla_con=RuntimeError("boom 123456"))


def test_primer_fallo_deja_pendiente_y_suma_intento(usuario):
    noti = crear(usuario)
    correr(falla())
    noti.refresh_from_db()
    assert (noti.estado, noti.intentos) == (Notificacion.ESTADO_PENDIENTE, 1)
    assert noti.contexto == {"codigo": "123456"}
    assert "123456" not in noti.error


def test_tercer_fallo_marca_fallida_y_vacia_el_contexto(usuario):
    noti = crear(usuario)
    correr(falla(), 3)
    noti.refresh_from_db()
    assert (noti.estado, noti.intentos) == (Notificacion.ESTADO_FALLIDA, 3)
    assert noti.contexto == {}
    assert "123456" not in noti.error


def test_reintento_que_funciona_queda_enviada(usuario):
    noti = crear(usuario)
    correr(falla())
    correr(CanalFalso())
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_ENVIADA
    assert noti.contexto == {}


def test_whatsapp_al_tercer_fallo_crea_copia_por_correo(usuario):
    noti = crear(usuario, canal="whatsapp")
    correr(falla(), 3)
    noti.refresh_from_db()
    copia = Notificacion.objects.get(canal="correo")
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert copia.plantilla == noti.plantilla
    assert copia.contexto == {"codigo": "123456"}
    assert copia.intentos == 0
    assert copia.estado == Notificacion.ESTADO_PENDIENTE
    assert copia.creado_en == noti.creado_en


def test_whatsapp_antes_del_tercer_fallo_no_crea_copia(usuario):
    crear(usuario, canal="whatsapp")
    correr(falla(), 2)
    assert not Notificacion.objects.filter(canal="correo").exists()


@pytest.mark.parametrize("canal", ["correo", "consola"])
def test_correo_y_consola_no_crean_copia(usuario, canal):
    crear(usuario, canal=canal)
    correr(falla(), 3)
    assert Notificacion.objects.count() == 1


def vencida(usuario, canal="consola", **ctx):
    contexto = {"codigo": "123456", "minutos": 10, **ctx}
    noti = crear(usuario, canal=canal, contexto=contexto)
    Notificacion.objects.filter(pk=noti.pk).update(creado_en=timezone.now() - timedelta(minutes=11))
    return noti


def test_codigo_vencido_no_se_envia_ni_se_reintenta(usuario):
    noti = vencida(usuario)
    canal = CanalFalso()
    correr(canal)
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert "Código vencido" in noti.error
    assert noti.contexto == {}
    assert canal.enviados == []
    assert noti.intentos == 0


def test_codigo_vencido_en_el_tercer_fallo_no_crea_copia(usuario):
    noti = crear(usuario, canal="whatsapp", contexto={"codigo": "123456", "minutos": 10})
    correr(falla(), 2)
    Notificacion.objects.filter(pk=noti.pk).update(creado_en=timezone.now() - timedelta(minutes=11))
    noti.refresh_from_db()
    # Vence justo entre el segundo y el tercer fallo: manejar_fallo no debe respaldar.
    worker.manejar_fallo(noti, RuntimeError("boom"))
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert not Notificacion.objects.filter(canal="correo").exists()


@pytest.mark.parametrize("minutos", [None, "abc", "falta"])
def test_minutos_invalidos_no_truenan(usuario, minutos):
    contexto = {"codigo": "123456"}
    if minutos != "falta":
        contexto["minutos"] = minutos
    noti = crear(usuario, contexto=contexto)
    Notificacion.objects.filter(pk=noti.pk).update(creado_en=timezone.now() - timedelta(days=1))
    canal = CanalFalso()
    correr(canal)
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_ENVIADA
    assert len(canal.enviados) == 1


def test_notificacion_sin_codigo_no_vence(usuario):
    noti = crear(usuario, contexto={"minutos": 1})
    Notificacion.objects.filter(pk=noti.pk).update(creado_en=timezone.now() - timedelta(days=1))
    assert worker.codigo_vencido(Notificacion.objects.get(pk=noti.pk)) is False
