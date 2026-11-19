import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password

from notificaciones.models import Notificacion
from usuarios.codigos import crear_codigo, generar_codigo, sortear_codigo
from usuarios.models import Canal, CodigoVerificacion, Proposito
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_sortear_codigo_tiene_6_digitos():
    for _ in range(200):
        assert re.fullmatch(r"\d{6}", sortear_codigo())


def test_sortear_codigo_rellena_con_ceros(monkeypatch):
    monkeypatch.setattr("usuarios.codigos.secrets.randbelow", lambda n: 42)
    assert sortear_codigo() == "000042"


def test_crear_codigo_devuelve_el_codigo_en_claro_y_guarda_el_hash():
    registro, codigo = crear_codigo(UsuarioFactory(), Proposito.ACTIVACION)
    assert registro.codigo_hash != codigo
    assert check_password(codigo, registro.codigo_hash)


def test_generar_codigo_guarda_solo_el_hash():
    usuario = UsuarioFactory()
    registro = generar_codigo(usuario, Proposito.ACTIVACION)
    codigo = Notificacion.objects.get(destinatario=usuario).contexto["codigo"]
    assert registro.codigo_hash != codigo
    assert check_password(codigo, registro.codigo_hash)


def test_generar_codigo_encola_una_notificacion_pendiente():
    usuario = UsuarioFactory()
    generar_codigo(usuario, Proposito.ACTIVACION)
    noti = Notificacion.objects.get(destinatario=usuario)
    assert noti.estado == Notificacion.ESTADO_PENDIENTE
    assert noti.plantilla == "codigo_activacion"
    assert noti.canal == "correo"
    assert noti.contexto["nombre"] == "Ana"
    assert noti.contexto["minutos"] == 10


def test_la_plantilla_depende_del_proposito():
    usuario = UsuarioFactory()
    generar_codigo(usuario, Proposito.RECUPERACION)
    assert Notificacion.objects.get(destinatario=usuario).plantilla == "codigo_recuperacion"


def test_usa_el_canal_indicado():
    usuario = UsuarioFactory()
    registro = generar_codigo(usuario, Proposito.ACTIVACION, Canal.WHATSAPP)
    assert registro.canal == Canal.WHATSAPP
    assert Notificacion.objects.get(destinatario=usuario).canal == "whatsapp"


def test_sin_canal_usa_el_preferido_del_usuario():
    usuario = UsuarioFactory(canal_preferido=Canal.WHATSAPP)
    registro = generar_codigo(usuario, Proposito.ACTIVACION)
    assert registro.canal == Canal.WHATSAPP


def test_whatsapp_sin_telefono_usa_correo():
    usuario = UsuarioFactory(telefono=None, canal_preferido=Canal.WHATSAPP)
    registro = generar_codigo(usuario, Proposito.ACTIVACION)
    assert registro.canal == Canal.CORREO
    assert Notificacion.objects.get(destinatario=usuario).canal == "correo"


def test_canal_desconocido_no_crea_nada():
    with pytest.raises(ValueError):
        generar_codigo(UsuarioFactory(), Proposito.ACTIVACION, "sms")
    assert not CodigoVerificacion.objects.exists()
    assert not Notificacion.objects.exists()


def test_la_vigencia_sale_del_setting(settings):
    settings.CODIGO_MINUTOS = 5
    registro = generar_codigo(UsuarioFactory(), Proposito.ACTIVACION)
    duracion = registro.expira_en - registro.creado_en
    assert timedelta(minutes=4, seconds=55) < duracion <= timedelta(minutes=5)


def test_un_codigo_nuevo_anula_el_anterior():
    usuario = UsuarioFactory()
    primero = generar_codigo(usuario, Proposito.ACTIVACION)
    segundo = generar_codigo(usuario, Proposito.ACTIVACION)
    primero.refresh_from_db()
    assert primero.usado is True
    assert segundo.usado is False


def test_si_falla_el_encolado_no_queda_codigo(monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("falla el encolado")

    monkeypatch.setattr("usuarios.codigos.notificar", falla)
    with pytest.raises(RuntimeError):
        generar_codigo(UsuarioFactory(), Proposito.ACTIVACION)
    assert not CodigoVerificacion.objects.exists()
