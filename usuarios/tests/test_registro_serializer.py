"""HU-02 / ST-65: pruebas de RegistroSerializer."""
import pytest
from django.contrib.auth.hashers import check_password
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from comun.roles import Rol
from usuarios.models import Canal, Estado, Usuario
from usuarios.serializers import CORREO_REGISTRADO, TELEFONO_REGISTRADO, RegistroSerializer
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def datos_validos(**cambios):
    datos = {
        "nombre": "María",
        "apellidos": "Hernández Ruiz",
        "correo": "maria.hernandez@ejemplo.com",
        "telefono": "443 123 4567",
        "password": "Registro2026",
        "password_confirmacion": "Registro2026",
        "canal_preferido": Canal.WHATSAPP,
        "acepto_privacidad": True,
    }
    datos.update(cambios)
    return datos


def errores(datos):
    serializer = RegistroSerializer(data=datos)
    assert not serializer.is_valid()
    return serializer.errors


# Caso feliz

@override_settings(VERSION_AVISO_PRIVACIDAD="2026-1")
def test_crea_cuenta_pendiente_de_cliente_con_privacidad():
    serializer = RegistroSerializer(data=datos_validos())
    assert serializer.is_valid(), serializer.errors
    usuario = serializer.save()

    assert usuario.first_name == "María"
    assert usuario.last_name == "Hernández Ruiz"
    assert usuario.canal_preferido == Canal.WHATSAPP
    assert usuario.estado == Estado.PENDIENTE
    assert usuario.rol == Rol.CLIENTE
    assert usuario.is_staff is False and usuario.is_superuser is False
    assert usuario.acepto_privacidad_en is not None
    assert usuario.version_privacidad == "2026-1"


def test_canal_preferido_por_defecto_es_correo():
    datos = datos_validos()
    del datos["canal_preferido"]
    serializer = RegistroSerializer(data=datos)
    assert serializer.is_valid(), serializer.errors
    assert serializer.save().canal_preferido == Canal.CORREO


def test_ignora_rol_y_estado_enviados_por_el_cliente():
    serializer = RegistroSerializer(data=datos_validos(rol=Rol.ADMINISTRADOR, estado=Estado.ACTIVO))
    assert serializer.is_valid(), serializer.errors
    usuario = serializer.save()
    assert usuario.rol == Rol.CLIENTE
    assert usuario.estado == Estado.PENDIENTE


# Contraseñas write_only

def test_password_se_guarda_como_hash_y_no_sale_en_la_respuesta():
    serializer = RegistroSerializer(data=datos_validos())
    assert serializer.is_valid(), serializer.errors
    usuario = serializer.save()

    assert usuario.password != "Registro2026"
    assert check_password("Registro2026", usuario.password)
    assert "password" not in serializer.data
    assert "password_confirmacion" not in serializer.data
    assert "acepto_privacidad" not in serializer.data


# Normalización

def test_normaliza_correo_y_telefono():
    datos = datos_validos(correo="  Maria.Hernandez@Ejemplo.COM ", telefono="+52 443 123 4567")
    serializer = RegistroSerializer(data=datos)
    assert serializer.is_valid(), serializer.errors
    usuario = serializer.save()
    assert usuario.email == "maria.hernandez@ejemplo.com"
    assert usuario.telefono == "+524431234567"


def test_rechaza_telefono_invalido():
    assert "telefono" in errores(datos_validos(telefono="123"))


# Duplicados

def test_rechaza_correo_registrado_sin_importar_mayusculas():
    UsuarioFactory(email="maria.hernandez@ejemplo.com")
    assert errores(datos_validos(correo="MARIA.Hernandez@ejemplo.com"))["correo"] == [CORREO_REGISTRADO]


def test_rechaza_telefono_registrado_aunque_se_escriba_distinto():
    UsuarioFactory(telefono="+524431234567")
    assert errores(datos_validos(telefono="443-123-4567"))["telefono"] == [TELEFONO_REGISTRADO]


@pytest.mark.parametrize(
    ("existente", "campo", "mensaje"),
    [
        ({"email": "maria.hernandez@ejemplo.com"}, "correo", CORREO_REGISTRADO),
        ({"telefono": "+524431234567"}, "telefono", TELEFONO_REGISTRADO),
    ],
)
def test_registro_simultaneo_responde_error_de_validacion(existente, campo, mensaje):
    """Otra petición registró el mismo dato entre la validación y el guardado."""
    serializer = RegistroSerializer(data=datos_validos())
    assert serializer.is_valid(), serializer.errors
    UsuarioFactory(**existente)
    with pytest.raises(ValidationError) as error:
        serializer.save()
    assert error.value.detail[campo] == [mensaje]


# Política de contraseñas

def test_rechaza_contrasenas_que_no_coinciden():
    assert "password_confirmacion" in errores(datos_validos(password_confirmacion="Otra12345"))


@pytest.mark.parametrize(
    "password",
    [
        "Corta1",  # menos de 8 caracteres
        "sinmayuscula123",  # sin mayúscula
        "SinNumeroAqui",  # sin número
        "Password123",  # contraseña común
    ],
)
def test_rechaza_contrasena_que_no_cumple_la_politica(password):
    resultado = errores(datos_validos(password=password, password_confirmacion=password))
    assert "password" in resultado


def test_rechaza_contrasena_parecida_al_correo():
    resultado = errores(
        datos_validos(correo="registro2026@ejemplo.com", password="Registro2026", password_confirmacion="Registro2026")
    )
    assert "password" in resultado


# Aviso de privacidad

@pytest.mark.parametrize("valor", [False, None])
def test_sin_aceptar_privacidad_no_se_crea_la_cuenta(valor):
    datos = datos_validos(acepto_privacidad=valor)
    if valor is None:
        del datos["acepto_privacidad"]
    assert "acepto_privacidad" in errores(datos)
    assert not Usuario.objects.exists()


# Campos obligatorios

@pytest.mark.parametrize("campo", ["nombre", "apellidos", "correo", "telefono", "password", "password_confirmacion"])
def test_campos_obligatorios(campo):
    datos = datos_validos()
    del datos[campo]
    assert campo in errores(datos)