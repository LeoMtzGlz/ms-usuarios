"""HU-15 / ST-140: pruebas del endpoint POST /api/v1/usuarios/ (alta de operativo)."""
import logging

import pytest
from django.db import IntegrityError
from rest_framework_simplejwt.tokens import RefreshToken

from comun.roles import Rol
from usuarios.models import Estado, Usuario , Zona
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/usuarios/"


def datos_validos(**cambios):
    zona, _ = Zona.objects.get_or_create(
        nombre="Centro",
        defaults={"activa": True},
    )

    datos = {
        "nombre": "Luis",
        "apellidos": "Ramírez Soto",
        "correo": "luis.ramirez@ejemplo.com",
        "telefono": "443 123 4567",
        "zona": zona.pk,
    }

    datos.update(cambios)
    return datos


def cliente_como(api_client, usuario, **claims):
    """Autentica con un token que lleva el claim `rol`, como el que emite usuarios/tokens.py."""
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    for nombre, valor in claims.items():
        acceso[nombre] = valor
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api_client


@pytest.fixture
def admin(llaves):
    return UsuarioFactory(rol=Rol.ADMINISTRADOR)


@pytest.fixture
def cliente_admin(api_client, admin):
    return cliente_como(api_client, admin)


# --- Alta correcta -------------------------------------------------------------------


def test_alta_correcta_responde_201_con_los_datos_y_la_contrasena(cliente_admin):
    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Luis"
    assert cuerpo["apellidos"] == "Ramírez Soto"
    assert cuerpo["correo"] == "luis.ramirez@ejemplo.com"
    assert cuerpo["telefono"] == "+524431234567"
    assert cuerpo["rol"] == Rol.OPERATIVO
    assert cuerpo["estado"] == Estado.ACTIVO
    assert cuerpo["debe_cambiar_password"] is True
    assert len(cuerpo["contrasena_temporal"]) == 12


def test_la_cuenta_queda_activa_operativa_y_con_contrasena_temporal(cliente_admin):
    cliente_admin.post(URL, datos_validos(), format="json")

    usuario = Usuario.objects.get(email="luis.ramirez@ejemplo.com")
    assert usuario.rol == Rol.OPERATIVO
    assert usuario.estado == Estado.ACTIVO
    assert usuario.is_active is True
    assert usuario.debe_cambiar_password is True
    assert usuario.is_staff is False
    assert usuario.is_superuser is False


def test_la_contrasena_devuelta_es_la_que_se_guardo_y_solo_se_guarda_su_hash(cliente_admin):
    contrasena = cliente_admin.post(URL, datos_validos(), format="json").json()["contrasena_temporal"]

    usuario = Usuario.objects.get(email="luis.ramirez@ejemplo.com")
    assert usuario.check_password(contrasena)
    assert usuario.password != contrasena
    assert contrasena not in usuario.password
    assert usuario.password.startswith("argon2")


def test_cada_alta_genera_una_contrasena_distinta(cliente_admin):
    primera = cliente_admin.post(URL, datos_validos(), format="json").json()["contrasena_temporal"]
    segunda = cliente_admin.post(
        URL, datos_validos(correo="otro@ejemplo.com", telefono="443 765 4321"), format="json"
    ).json()["contrasena_temporal"]

    assert primera != segunda


def test_la_respuesta_no_se_guarda_en_cache(cliente_admin):
    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta["Cache-Control"] == "no-store"


def test_normaliza_correo_y_telefono(cliente_admin):
    respuesta = cliente_admin.post(
        URL, datos_validos(correo="  Luis.Ramirez@Ejemplo.COM ", telefono="+52 443 123 4567"), format="json"
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["correo"] == "luis.ramirez@ejemplo.com"
    assert respuesta.json()["telefono"] == "+524431234567"


def test_ignora_rol_estado_y_permisos_enviados_por_el_cliente(cliente_admin):
    respuesta = cliente_admin.post(
        URL,
        datos_validos(
            rol=Rol.ADMINISTRADOR,
            estado=Estado.PENDIENTE,
            is_staff=True,
            is_superuser=True,
            debe_cambiar_password=False,
            password="Mia12345",
        ),
        format="json",
    )

    assert respuesta.status_code == 201
    usuario = Usuario.objects.get(email="luis.ramirez@ejemplo.com")
    assert usuario.rol == Rol.OPERATIVO
    assert usuario.estado == Estado.ACTIVO
    assert usuario.is_staff is False
    assert usuario.is_superuser is False
    assert usuario.debe_cambiar_password is True
    assert not usuario.check_password("Mia12345")


# --- Quién puede darlo de alta -------------------------------------------------------


def test_sin_token_responde_401(api_client, llaves):
    respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"
    assert not Usuario.objects.filter(email="luis.ramirez@ejemplo.com").exists()


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_un_no_administrador_recibe_403(api_client, llaves, rol):
    cliente_como(api_client, UsuarioFactory(rol=rol))

    respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"
    assert not Usuario.objects.filter(email="luis.ramirez@ejemplo.com").exists()


def test_un_administrador_con_contrasena_temporal_recibe_403(api_client, admin):
    cliente_como(api_client, admin, debe_cambiar_password=True)

    respuesta = api_client.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"


def test_solo_acepta_post(cliente_admin):
    assert cliente_admin.delete(URL).status_code == 405


# --- Validaciones --------------------------------------------------------------------


def test_correo_duplicado_responde_400(cliente_admin):
    UsuarioFactory(email="luis.ramirez@ejemplo.com")

    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert respuesta.json()["campos"]["correo"] == ["Este correo ya está registrado."]


def test_correo_duplicado_sin_importar_mayusculas(cliente_admin):
    UsuarioFactory(email="luis.ramirez@ejemplo.com")

    respuesta = cliente_admin.post(URL, datos_validos(correo="LUIS.RAMIREZ@EJEMPLO.COM"), format="json")

    assert respuesta.status_code == 400
    assert "correo" in respuesta.json()["campos"]


def test_telefono_duplicado_responde_400(cliente_admin):
    UsuarioFactory(telefono="+524431234567")

    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert respuesta.json()["campos"]["telefono"] == ["Este teléfono ya está registrado."]


def test_telefono_invalido_responde_400(cliente_admin):
    respuesta = cliente_admin.post(URL, datos_validos(telefono="123"), format="json")

    assert respuesta.status_code == 400
    assert "telefono" in respuesta.json()["campos"]


def test_correo_invalido_responde_400(cliente_admin):
    respuesta = cliente_admin.post(URL, datos_validos(correo="no-es-un-correo"), format="json")

    assert respuesta.status_code == 400
    assert "correo" in respuesta.json()["campos"]


@pytest.mark.parametrize("campo", ["nombre", "apellidos", "correo", "telefono", "zona"]) 
def test_faltan_campos_obligatorios(cliente_admin, campo):
    datos = datos_validos()
    del datos[campo]

    respuesta = cliente_admin.post(URL, datos, format="json")

    assert respuesta.status_code == 400
    assert campo in respuesta.json()["campos"]


def test_un_intento_fallido_no_crea_cuentas(cliente_admin):
    antes = Usuario.objects.count()

    cliente_admin.post(URL, datos_validos(correo="no-es-un-correo"), format="json")

    assert Usuario.objects.count() == antes


def test_alta_simultanea_con_el_mismo_correo_responde_400(cliente_admin, monkeypatch):
    """Si dos altas pasan la validación a la vez, la restricción única de la base las frena."""

    def choca(*args, **kwargs):
        raise IntegrityError('duplicate key value violates unique constraint "email_unico_ci"')

    monkeypatch.setattr(Usuario.objects, "create_user", choca)

    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["campos"]["correo"] == ["Este correo ya está registrado."]


# --- La contraseña no se filtra ------------------------------------------------------


def test_la_contrasena_no_aparece_en_la_bitacora(cliente_admin, caplog):
    with caplog.at_level(logging.INFO, logger="svc.auditoria"):
        contrasena = cliente_admin.post(URL, datos_validos(), format="json").json()["contrasena_temporal"]

    assert "alta_usuario" in caplog.text
    assert contrasena not in caplog.text


def test_la_bitacora_registra_quien_creo_la_cuenta(cliente_admin, admin, caplog):
    with caplog.at_level(logging.INFO, logger="svc.auditoria"):
        cliente_admin.post(URL, datos_validos(), format="json")

    assert str(admin.pk) in caplog.text
    assert Rol.OPERATIVO in caplog.text
