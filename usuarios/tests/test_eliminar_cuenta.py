"""HU-23 / ST-174: POST /api/v1/auth/eliminar-cuenta/"""
from unittest import mock

import pytest
from django.core import mail

from comun.roles import Rol
from usuarios.anonimizacion import esta_anonimizado
from usuarios.models import Estado, Usuario
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/eliminar-cuenta/"
PROTEGIDO = "/api/v1/auth/privacidad/aceptar/"


def eliminar(api_client, usuario, **cambios):
    api_client.force_authenticate(user=usuario)
    datos = {"password": PASSWORD_PRUEBA, "confirmacion": "ELIMINAR"}
    datos.update(cambios)
    return api_client.post(URL, datos, format="json")


def test_elimina_la_cuenta_y_la_deja_anonimizada_e_inactiva(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com", first_name="Ana", telefono="+524431230001")
    respuesta = eliminar(api_client, usuario)

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert esta_anonimizado(usuario)
    assert usuario.estado == Estado.INACTIVO and not usuario.is_active
    assert usuario.telefono is None
    assert usuario.first_name == "Usuario"
    assert not usuario.has_usable_password()
    assert Usuario.objects.filter(pk=usuario.pk).exists()  # los registros relacionados se conservan


def test_el_correo_queda_libre_para_registrarse_de_nuevo(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    eliminar(api_client, usuario)

    assert not Usuario.objects.filter(email="ana@ejemplo.com").exists()
    UsuarioFactory(email="ana@ejemplo.com")


def test_envia_el_correo_de_confirmacion_al_correo_original(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    eliminar(api_client, usuario)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ana@ejemplo.com"]
    assert "eliminada" in mail.outbox[0].subject.lower()


def test_el_correo_sale_antes_de_anonimizar(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    orden = []
    with mock.patch("usuarios.eliminacion.CanalCorreo.enviar", side_effect=lambda *a, **k: orden.append("correo")), \
         mock.patch("usuarios.eliminacion.anonimizar_usuario", side_effect=lambda *a, **k: orden.append("anonimizar")):
        eliminar(api_client, usuario)

    assert orden == ["correo", "anonimizar"]


def test_si_falla_el_correo_la_cuenta_se_elimina_igual(api_client):
    usuario = UsuarioFactory()
    with mock.patch("usuarios.eliminacion.CanalCorreo.enviar", side_effect=RuntimeError("smtp caído")):
        respuesta = eliminar(api_client, usuario)

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert esta_anonimizado(usuario)


def test_cierra_todas_las_sesiones(api_client, llaves):
    UsuarioFactory(email="ana@ejemplo.com")
    login = api_client.post("/api/v1/auth/login/", {"email": "ana@ejemplo.com", "password": PASSWORD_PRUEBA})
    assert login.status_code == 200
    token = login.json()["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    datos = {"password": PASSWORD_PRUEBA, "confirmacion": "ELIMINAR"}
    assert api_client.post(URL, datos, format="json").status_code == 200

    # el mismo token ya no sirve
    assert api_client.post(PROTEGIDO, {}, format="json").status_code == 401


# Validaciones

def test_contrasena_incorrecta_responde_400_y_no_elimina(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    respuesta = eliminar(api_client, usuario, password="Incorrecta123")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert "password" in respuesta.json()["campos"]
    usuario.refresh_from_db()
    assert usuario.email == "ana@ejemplo.com" and usuario.estado == Estado.ACTIVO
    assert not mail.outbox


@pytest.mark.parametrize("palabra", ["eliminar", "Eliminar", "ELIMINA", "", "BORRAR"])
def test_la_palabra_debe_ser_exactamente_eliminar(api_client, palabra):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    respuesta = eliminar(api_client, usuario, confirmacion=palabra)

    assert respuesta.status_code == 400
    assert "confirmacion" in respuesta.json()["campos"]
    usuario.refresh_from_db()
    assert usuario.email == "ana@ejemplo.com"
    assert not mail.outbox


@pytest.mark.parametrize("campo", ["password", "confirmacion"])
def test_faltan_campos_obligatorios(api_client, campo):
    usuario = UsuarioFactory()
    api_client.force_authenticate(user=usuario)
    datos = {"password": PASSWORD_PRUEBA, "confirmacion": "ELIMINAR"}
    del datos[campo]
    respuesta = api_client.post(URL, datos, format="json")

    assert respuesta.status_code == 400
    assert campo in respuesta.json()["campos"]


def test_sin_sesion_responde_401(api_client):
    respuesta = api_client.post(URL, {"password": PASSWORD_PRUEBA, "confirmacion": "ELIMINAR"}, format="json")
    assert respuesta.status_code == 401


def test_solo_acepta_post(api_client):
    api_client.force_authenticate(user=UsuarioFactory())
    assert api_client.get(URL).status_code == 405


# Único administrador

def test_el_unico_administrador_no_puede_eliminarse(api_client):
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR, email="admin@ejemplo.com")
    respuesta = eliminar(api_client, admin)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "unico_administrador"
    admin.refresh_from_db()
    assert admin.email == "admin@ejemplo.com" and admin.estado == Estado.ACTIVO
    assert not mail.outbox


def test_un_administrador_puede_eliminarse_si_hay_otro_activo(api_client):
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR)
    UsuarioFactory(rol=Rol.ADMINISTRADOR)
    assert eliminar(api_client, admin).status_code == 200


def test_otro_administrador_inactivo_no_cuenta(api_client):
    admin = UsuarioFactory(rol=Rol.ADMINISTRADOR)
    UsuarioFactory(rol=Rol.ADMINISTRADOR, estado=Estado.INACTIVO)
    assert eliminar(api_client, admin).status_code == 403


def test_un_cliente_puede_eliminarse_aunque_haya_un_solo_admin(api_client):
    UsuarioFactory(rol=Rol.ADMINISTRADOR)
    cliente = UsuarioFactory(rol=Rol.CLIENTE)
    assert eliminar(api_client, cliente).status_code == 200


def test_no_toca_a_otros_usuarios(api_client):
    otro = UsuarioFactory(email="otro@ejemplo.com")
    eliminar(api_client, UsuarioFactory())
    otro.refresh_from_db()
    assert otro.email == "otro@ejemplo.com" and otro.estado == Estado.ACTIVO


def test_no_revela_la_contrasena_ni_datos_en_la_respuesta(api_client):
    usuario = UsuarioFactory(email="ana@ejemplo.com")
    respuesta = eliminar(api_client, usuario)
    assert "ana@ejemplo.com" not in respuesta.content.decode()
    assert PASSWORD_PRUEBA not in respuesta.content.decode()