"""HU-02 / ST-68: casos de error del registro, probados por HTTP (POST /api/v1/auth/registro/).

Los mismos casos ya se prueban a nivel serializer en test_registro_serializer.py;
aquí se comprueba lo que solo se ve por la API: el código HTTP, el formato estándar del error
y que, si algo falla, no se crea nada.
"""
import pytest

from notificaciones.models import Notificacion
from usuarios.models import CodigoVerificacion, Usuario
from usuarios.serializers import CORREO_REGISTRADO, TELEFONO_REGISTRADO
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/registro/"


def datos_validos(**cambios):
    datos = {
        "nombre": "María",
        "apellidos": "Hernández Ruiz",
        "correo": "maria.hernandez@ejemplo.com",
        "telefono": "443 123 4567",
        "password": "Registro2026",
        "password_confirmacion": "Registro2026",
        "canal_preferido": "correo",
        "acepto_privacidad": True,
    }
    datos.update(cambios)
    return datos


def registrar(api_client, **cambios):
    return api_client.post(URL, datos_validos(**cambios), format="json")


def assert_error_de_validacion(respuesta, campo):
    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "datos_invalidos"
    assert campo in cuerpo["campos"]
    return cuerpo["campos"][campo]


def assert_no_se_creo_nada(cuentas_antes=0):
    assert Usuario.objects.count() == cuentas_antes
    assert not CodigoVerificacion.objects.exists()
    assert not Notificacion.objects.exists()


def test_telefono_duplicado_escrito_distinto_responde_400(api_client):
    UsuarioFactory(telefono="+524431234567")
    respuesta = registrar(api_client, telefono="443-123-4567")

    assert assert_error_de_validacion(respuesta, "telefono") == [TELEFONO_REGISTRADO]
    assert_no_se_creo_nada(cuentas_antes=1)


def test_correo_duplicado_con_mayusculas_no_crea_nada(api_client):
    UsuarioFactory(email="maria.hernandez@ejemplo.com")
    respuesta = registrar(api_client, correo="MARIA.Hernandez@EJEMPLO.com")

    assert assert_error_de_validacion(respuesta, "correo") == [CORREO_REGISTRADO]
    assert_no_se_creo_nada(cuentas_antes=1)


def test_contrasenas_distintas_responden_400(api_client):
    respuesta = registrar(api_client, password_confirmacion="Otra12345")

    assert assert_error_de_validacion(respuesta, "password_confirmacion") == ["Las contraseñas no coinciden."]
    assert_no_se_creo_nada()


@pytest.mark.parametrize("password", ["Corta1", "sinmayuscula123", "SinNumeroAqui", "Password123"])
def test_contrasena_debil_responde_400(api_client, password):
    respuesta = registrar(api_client, password=password, password_confirmacion=password)

    assert assert_error_de_validacion(respuesta, "password")
    assert_no_se_creo_nada()


@pytest.mark.parametrize("valor", [False, None])
def test_sin_aceptar_el_aviso_de_privacidad_responde_400(api_client, valor):
    datos = datos_validos(acepto_privacidad=valor)
    if valor is None:
        del datos["acepto_privacidad"]
    respuesta = api_client.post(URL, datos, format="json")

    assert assert_error_de_validacion(respuesta, "acepto_privacidad")
    assert_no_se_creo_nada()


@pytest.mark.parametrize("campo", ["nombre", "apellidos", "correo", "telefono", "password", "password_confirmacion"])
def test_falta_un_campo_obligatorio_responde_400(api_client, campo):
    datos = datos_validos()
    del datos[campo]
    respuesta = api_client.post(URL, datos, format="json")

    assert assert_error_de_validacion(respuesta, campo)
    assert_no_se_creo_nada()


def test_la_respuesta_de_error_nunca_devuelve_la_contrasena(api_client):
    respuesta = registrar(api_client, password_confirmacion="Otra12345")

    assert "Registro2026" not in respuesta.content.decode()
    assert "Otra12345" not in respuesta.content.decode()