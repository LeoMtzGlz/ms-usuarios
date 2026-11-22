"""t-10/st-54: pruebas de flujo del worker, de varios ciclos de procesar_lote cada una."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from notificaciones import worker
from notificaciones.models import Notificacion
from notificaciones.tests.test_worker import (  # noqa: F401  (plantillas es fixture autouse)
    CanalFalso, crear, plantillas, resolver_con,
)

pytestmark = pytest.mark.django_db

FALLO = RuntimeError("Meta rechazó el código 123456")


def ciclo(canal):
    return worker.procesar_lote(obtener_canal=resolver_con(canal))


def por_canal(**canales):
    """Resolver que entrega un canal distinto según el canal de la notificación."""
    return lambda nombre: canales[nombre]


def envejecer(noti, minutos):
    Notificacion.objects.filter(pk=noti.pk).update(creado_en=timezone.now() - timedelta(minutes=minutos))


def test_exito_en_el_primer_ciclo(usuario):
    noti = crear(usuario)
    canal = CanalFalso()
    assert ciclo(canal).enviadas == 1
    noti.refresh_from_db()
    assert (noti.estado, noti.intentos, noti.contexto) == (Notificacion.ESTADO_ENVIADA, 0, {})
    assert ciclo(canal).total == 0
    assert len(canal.enviados) == 1


def test_falla_dos_veces_y_sale_al_tercer_ciclo(usuario):
    noti = crear(usuario)
    mal, bien = CanalFalso(falla_con=FALLO), CanalFalso()
    for esperado in (1, 2):
        assert ciclo(mal).fallidas == 1
        noti.refresh_from_db()
        assert (noti.estado, noti.intentos) == (Notificacion.ESTADO_PENDIENTE, esperado)
        assert noti.contexto == {"codigo": "123456"}
    assert ciclo(bien).enviadas == 1
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_ENVIADA
    assert noti.contexto == {}
    assert noti.error == ""
    assert [e[2] for e in bien.enviados] == ["Tu código es 123456"]


def test_whatsapp_agota_intentos_y_la_copia_sale_por_correo(usuario):
    noti = crear(usuario, canal="whatsapp")
    creado = noti.creado_en
    resolver = por_canal(whatsapp=CanalFalso(falla_con=FALLO), correo=(correo := CanalFalso()))
    for _ in range(3):
        assert worker.procesar_lote(obtener_canal=resolver).fallidas == 1
    noti.refresh_from_db()
    copia = Notificacion.objects.get(canal="correo")
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert (copia.estado, copia.intentos, copia.creado_en) == (Notificacion.ESTADO_PENDIENTE, 0, creado)
    assert correo.enviados == []

    resultado = worker.procesar_lote(obtener_canal=resolver)  # ciclo 4

    copia.refresh_from_db()
    assert resultado.enviadas == 1
    assert copia.estado == Notificacion.ESTADO_ENVIADA
    assert copia.contexto == {}
    assert correo.enviados == [(usuario.email, worker.ASUNTO_POR_DEFECTO, "Tu código es 123456")]
    assert worker.procesar_lote(obtener_canal=resolver).total == 0
    assert Notificacion.objects.count() == 2


def test_correo_agota_intentos_y_queda_fallida_sin_copia(usuario):
    noti = crear(usuario, canal="correo")
    mal = CanalFalso(falla_con=FALLO)
    for _ in range(3):
        assert ciclo(mal).fallidas == 1
    noti.refresh_from_db()
    assert (noti.estado, noti.intentos, noti.contexto) == (Notificacion.ESTADO_FALLIDA, 3, {})
    assert ciclo(mal).total == 0
    assert Notificacion.objects.count() == 1


def test_codigo_vencido_no_se_envia(usuario):
    noti = crear(usuario, contexto={"codigo": "123456", "minutos": 10})
    envejecer(noti, 11)
    canal = CanalFalso()
    assert ciclo(canal).fallidas == 1
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert noti.error == "Código vencido: no se envió"
    assert noti.contexto == {}
    assert canal.enviados == []
    assert ciclo(canal).total == 0  # no se reintenta


def test_codigo_vencido_de_whatsapp_no_genera_copia(usuario):
    noti = crear(usuario, canal="whatsapp", contexto={"codigo": "123456", "minutos": 10})
    envejecer(noti, 11)
    ciclo(CanalFalso())
    assert Notificacion.objects.count() == 1


def test_codigo_vigente_si_se_envia(usuario):
    noti = crear(usuario, contexto={"codigo": "123456", "minutos": 10})
    envejecer(noti, 9)
    canal = CanalFalso()
    assert ciclo(canal).enviadas == 1
    noti.refresh_from_db()
    assert noti.estado == Notificacion.ESTADO_ENVIADA
    assert len(canal.enviados) == 1


def test_el_codigo_no_aparece_en_error_ni_en_el_contexto_final(usuario):
    noti = crear(usuario, contexto={"codigo": "123456", "minutos": 10})
    mal = CanalFalso(falla_con=FALLO)
    for i in range(3):
        ciclo(mal)
        noti.refresh_from_db()
        assert "123456" not in noti.error
        assert noti.error.startswith("RuntimeError")
        if i < 2:
            assert noti.contexto == {"codigo": "123456", "minutos": 10}
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert noti.contexto == {}
    assert noti.error.startswith("RuntimeError")


def test_un_lote_mixto(usuario):
    vencida = crear(usuario, contexto={"codigo": "111111", "minutos": 10})
    envejecer(vencida, 30)  # la más vieja: se procesa primero
    reintenta = crear(usuario, plantilla="no_existe")
    envia = crear(usuario)

    resultado = ciclo(CanalFalso())

    for n in (vencida, reintenta, envia):
        n.refresh_from_db()
    assert (resultado.enviadas, resultado.fallidas) == (1, 2)
    assert (vencida.estado, vencida.error) == (Notificacion.ESTADO_FALLIDA, "Código vencido: no se envió")
    assert (reintenta.estado, reintenta.intentos) == (Notificacion.ESTADO_PENDIENTE, 1)
    assert envia.estado == Notificacion.ESTADO_ENVIADA
    # al siguiente ciclo solo queda la que reintenta
    assert ciclo(CanalFalso()).total == 1


def test_el_comando_una_vez_aplica_los_reintentos(usuario, monkeypatch):
    noti = crear(usuario)
    monkeypatch.setattr(worker, "cargar_resolver", lambda: resolver_con(CanalFalso(falla_con=FALLO)))
    for esperado in (1, 2):
        call_command("procesar_notificaciones", "--una-vez")
        noti.refresh_from_db()
        assert (noti.estado, noti.intentos) == (Notificacion.ESTADO_PENDIENTE, esperado)
        assert noti.contexto == {"codigo": "123456"}
    call_command("procesar_notificaciones", "--una-vez")
    noti.refresh_from_db()
    assert (noti.estado, noti.intentos, noti.contexto) == (Notificacion.ESTADO_FALLIDA, 3, {})
