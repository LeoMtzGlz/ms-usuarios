"""t-10/st-51: pruebas del comando procesar_notificaciones y de su lógica.

No dependen de los canales reales (st-35/36/41/48): usan un canal falso que guarda lo
que se le pidió enviar, y una plantilla en memoria.
"""
import threading

import pytest
from django.core.management import CommandError, call_command
from django.db import connection, transaction
from django.test import override_settings

from notificaciones import worker
from notificaciones.models import Notificacion

PLANTILLAS_PRUEBA = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "OPTIONS": {
        "loaders": [("django.template.loaders.locmem.Loader", {
            "notificaciones/prueba.txt": "Tu código es {{ codigo }}",
        })],
    },
}]


class CanalFalso:
    def __init__(self, falla_con=None):
        self.enviados = []
        self.falla_con = falla_con

    def enviar(self, destino, asunto, texto):
        if self.falla_con:
            raise self.falla_con
        self.enviados.append((destino, asunto, texto))


def resolver_con(canal):
    return lambda nombre: canal


def crear(usuario, canal="consola", **extra):
    datos = {"plantilla": "prueba", "contexto": {"codigo": "123456"}}
    datos.update(extra)
    return Notificacion.objects.create(destinatario=usuario, canal=canal, **datos)


@pytest.fixture(autouse=True)
def plantillas():
    with override_settings(TEMPLATES=PLANTILLAS_PRUEBA):
        yield


@pytest.mark.django_db
def test_pendiente_pasa_a_enviada_y_se_vacia_el_codigo(usuario):
    noti = crear(usuario)
    canal = CanalFalso()

    resultado = worker.procesar_lote(obtener_canal=resolver_con(canal))

    noti.refresh_from_db()
    assert resultado.enviadas == 1
    assert noti.estado == Notificacion.ESTADO_ENVIADA
    assert noti.contexto == {}
    assert canal.enviados == [(usuario.email, worker.ASUNTO_POR_DEFECTO, "Tu código es 123456")]


@pytest.mark.django_db
def test_whatsapp_se_envia_al_telefono(usuario):
    crear(usuario, canal="whatsapp")
    canal = CanalFalso()

    worker.procesar_lote(obtener_canal=resolver_con(canal))

    assert canal.enviados[0][0] == usuario.telefono


@pytest.mark.django_db
def test_procesa_en_lotes_de_20_las_mas_viejas_primero(usuario):
    notis = [crear(usuario) for _ in range(25)]
    canal = CanalFalso()

    resultado = worker.procesar_lote(obtener_canal=resolver_con(canal))

    assert resultado.enviadas == 20
    pendientes = Notificacion.objects.filter(estado=Notificacion.ESTADO_PENDIENTE)
    assert set(pendientes.values_list("id", flat=True)) == {n.id for n in notis[20:]}


@pytest.mark.django_db
def test_no_toma_enviadas_ni_fallidas(usuario):
    crear(usuario, estado=Notificacion.ESTADO_ENVIADA)
    crear(usuario, estado=Notificacion.ESTADO_FALLIDA)
    canal = CanalFalso()

    resultado = worker.procesar_lote(obtener_canal=resolver_con(canal))

    assert resultado.total == 0
    assert canal.enviados == []


@pytest.mark.django_db
def test_si_el_canal_falla_queda_fallida_sin_el_codigo(usuario):
    noti = crear(usuario)
    canal = CanalFalso(falla_con=RuntimeError("Meta rechazó el código 123456"))

    resultado = worker.procesar_lote(obtener_canal=resolver_con(canal))

    noti.refresh_from_db()
    assert resultado.fallidas == 1
    assert noti.estado == Notificacion.ESTADO_FALLIDA
    assert "123456" not in noti.error
    assert noti.error.startswith("RuntimeError")


@pytest.mark.django_db
def test_un_fallo_no_detiene_el_resto_del_lote(usuario):
    mala = crear(usuario, plantilla="no_existe")
    buena = crear(usuario)

    resultado = worker.procesar_lote(obtener_canal=resolver_con(CanalFalso()))

    mala.refresh_from_db()
    buena.refresh_from_db()
    assert (resultado.enviadas, resultado.fallidas) == (1, 1)
    assert mala.estado == Notificacion.ESTADO_FALLIDA
    assert buena.estado == Notificacion.ESTADO_ENVIADA


@pytest.mark.django_db
def test_antes_de_enviar_puede_posponer(usuario, monkeypatch):
    """Punto de extensión de st-57: si dice que no, la notificación sigue pendiente."""
    noti = crear(usuario)
    monkeypatch.setattr(worker, "antes_de_enviar", lambda n: False)

    resultado = worker.procesar_lote(obtener_canal=resolver_con(CanalFalso()))

    noti.refresh_from_db()
    assert resultado.pospuestas == 1
    assert noti.estado == Notificacion.ESTADO_PENDIENTE


@pytest.mark.django_db(transaction=True)
def test_dos_workers_no_envian_la_misma(usuario):
    """Otro worker tiene bloqueada la fila: este se la salta (skip_locked)."""
    noti = crear(usuario)
    bloqueada = threading.Event()
    soltar = threading.Event()

    def otro_worker():
        try:
            with transaction.atomic():
                list(Notificacion.objects.select_for_update().filter(pk=noti.pk))
                bloqueada.set()
                soltar.wait(timeout=10)
        finally:
            connection.close()

    hilo = threading.Thread(target=otro_worker)
    hilo.start()
    assert bloqueada.wait(timeout=10)

    canal = CanalFalso()
    mientras_bloqueada = worker.procesar_lote(obtener_canal=resolver_con(canal))
    soltar.set()
    hilo.join()
    despues = worker.procesar_lote(obtener_canal=resolver_con(canal))

    assert mientras_bloqueada.total == 0
    assert despues.enviadas == 1
    assert len(canal.enviados) == 1


@pytest.mark.django_db
def test_comando_una_vez(usuario, monkeypatch):
    crear(usuario)
    canal = CanalFalso()
    monkeypatch.setattr(worker, "cargar_resolver", lambda: resolver_con(canal))

    call_command("procesar_notificaciones", "--una-vez")

    assert Notificacion.objects.get().estado == Notificacion.ESTADO_ENVIADA


@pytest.mark.django_db
def test_bucle_espera_5_s_y_se_detiene_con_sigterm(monkeypatch):
    from notificaciones.management.commands import procesar_notificaciones as comando

    manejadores, esperas, lotes = {}, [], []
    monkeypatch.setattr(worker, "cargar_resolver", lambda: resolver_con(CanalFalso()))
    monkeypatch.setattr(worker, "procesar_lote", lambda tamano, canal: lotes.append(tamano) or worker.Resultado())
    monkeypatch.setattr(comando.signal, "signal", lambda sig, fn: manejadores.__setitem__(sig, fn))

    def dormir(segundos):
        esperas.append(segundos)
        if len(esperas) == 2:  # docker compose stop a mitad de la segunda espera
            manejadores[comando.signal.SIGTERM](comando.signal.SIGTERM, None)

    monkeypatch.setattr(comando.time, "sleep", dormir)

    call_command("procesar_notificaciones")

    assert esperas == [5, 5]
    assert lotes == [20, 20]


def test_comando_avisa_si_faltan_los_canales(monkeypatch):
    def sin_canales():
        raise ImportError("no hay notificaciones.canales")

    monkeypatch.setattr(worker, "cargar_resolver", sin_canales)

    with pytest.raises(CommandError, match="st-35"):
        call_command("procesar_notificaciones", "--una-vez")
