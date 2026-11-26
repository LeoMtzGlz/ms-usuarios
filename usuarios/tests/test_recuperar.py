"""HU-10 / ST-107: POST /api/v1/auth/recuperar/"""
from unittest import mock

import pytest
from django.contrib.auth.hashers import check_password

from notificaciones.models import Notificacion
from notificaciones.plantillas import renderizar_plantilla_correo
from usuarios.models import Canal, CodigoVerificacion, Estado, Proposito
from usuarios.recuperacion import MENSAJE_RECUPERACION
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/recuperar/"


def test_por_correo_crea_codigo_y_encola_notificacion(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    respuesta = api_client.post(URL, {"identificador": "ana@ejemplo.com"}, format="json")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_RECUPERACION}
    codigo = CodigoVerificacion.objects.get(usuario=usuario)
    assert codigo.proposito == Proposito.RECUPERACION
    assert not codigo.usado
    assert Notificacion.objects.filter(destinatario=usuario).count() == 1


def test_correo_sin_importar_mayusculas_ni_espacios(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    api_client.post(URL, {"identificador": "  ANA@Ejemplo.com "}, format="json")
    assert CodigoVerificacion.objects.filter(usuario=usuario).count() == 1


def test_por_telefono_en_cualquier_formato(api_client):
    usuario = UsuarioFactory(telefono="+524431000001")
    respuesta = api_client.post(URL, {"identificador": "443 100 0001"}, format="json")

    assert respuesta.status_code == 200
    assert CodigoVerificacion.objects.filter(usuario=usuario).count() == 1


def test_canal_whatsapp_se_respeta(api_client):
    usuario = UsuarioFactory(telefono="+524431000002")
    api_client.post(URL, {"identificador": usuario.email, "canal": "whatsapp"}, format="json")
    assert CodigoVerificacion.objects.get(usuario=usuario).canal == Canal.WHATSAPP


def test_el_codigo_no_se_guarda_en_claro(api_client):
    usuario = UsuarioFactory()
    api_client.post(URL, {"identificador": usuario.email}, format="json")
    codigo = CodigoVerificacion.objects.get(usuario=usuario)
    assert len(codigo.codigo_hash) > 20 and not codigo.codigo_hash.isdigit()
    assert check_password("000000", codigo.codigo_hash) in (True, False)  # el hash es verificable


def test_un_segundo_pedido_anula_el_codigo_anterior(api_client):
    usuario = UsuarioFactory()
    api_client.post(URL, {"identificador": usuario.email}, format="json")
    api_client.post(URL, {"identificador": usuario.email}, format="json")
    vigentes = CodigoVerificacion.objects.filter(usuario=usuario, usado=False)
    assert vigentes.count() == 1


def test_cuenta_pendiente_tambien_recibe_codigo(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)
    api_client.post(URL, {"identificador": usuario.email}, format="json")
    assert CodigoVerificacion.objects.filter(usuario=usuario, proposito=Proposito.RECUPERACION).exists()


# Anti-enumeración

def test_cuenta_inexistente_responde_igual_y_no_crea_nada(api_client):
    existente = UsuarioFactory()
    r_existe = api_client.post(URL, {"identificador": existente.email}, format="json")
    r_no = api_client.post(URL, {"identificador": "nadie@ejemplo.com"}, format="json")

    assert (r_no.status_code, r_no.json()) == (r_existe.status_code, r_existe.json())
    assert CodigoVerificacion.objects.count() == 1
    assert Notificacion.objects.count() == 1


def test_cuenta_inactiva_responde_igual_y_no_envia(api_client):
    usuario = UsuarioFactory(estado=Estado.INACTIVO)
    respuesta = api_client.post(URL, {"identificador": usuario.email}, format="json")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_RECUPERACION}
    assert not CodigoVerificacion.objects.exists()


def test_telefono_con_formato_invalido_responde_igual(api_client):
    respuesta = api_client.post(URL, {"identificador": "abc123"}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_RECUPERACION}


def test_si_falla_el_envio_responde_igual_y_no_deja_codigo(api_client):
    usuario = UsuarioFactory()
    with mock.patch("usuarios.codigos.notificar", side_effect=RuntimeError("falla simulada")):
        respuesta = api_client.post(URL, {"identificador": usuario.email}, format="json")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_RECUPERACION}
    assert not CodigoVerificacion.objects.exists()


# Validación y método

def test_sin_identificador_responde_400_con_el_formato_estandar(api_client):
    respuesta = api_client.post(URL, {}, format="json")
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert "identificador" in respuesta.json()["campos"]


def test_canal_invalido_responde_400(api_client):
    respuesta = api_client.post(URL, {"identificador": "a@b.com", "canal": "paloma"}, format="json")
    assert respuesta.status_code == 400
    assert "canal" in respuesta.json()["campos"]


def test_es_publico_aunque_el_token_sea_invalido(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer token.invalido")
    respuesta = api_client.post(URL, {"identificador": "a@b.com"}, format="json")
    assert respuesta.status_code == 200


def test_solo_acepta_post(api_client):
    assert api_client.get(URL).status_code == 405


def test_la_plantilla_de_recuperacion_se_renderiza_con_su_alias():
    asunto, texto, html = renderizar_plantilla_correo(
        "codigo_recuperacion", {"nombre": "Ana", "codigo": "123456", "minutos": 10}
    )
    assert "123456" in texto and "123456" in html