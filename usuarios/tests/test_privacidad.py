"""t-02 / st-67: se guarda la aceptación del aviso de privacidad (fecha y versión)."""
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from usuarios.privacidad import datos_aceptacion_privacidad, revisar_version_aviso_privacidad, version_vigente
from usuarios.serializers import RegistroSerializer

pytestmark = pytest.mark.django_db


def datos_registro(**cambios):
    datos = {
        "nombre": "Ana",
        "apellidos": "López Pérez",
        "correo": "ana.lopez@ejemplo.com",
        "telefono": "353 123 4567",
        "password": "Privacidad2026",
        "password_confirmacion": "Privacidad2026",
        "acepto_privacidad": True,
    }
    datos.update(cambios)
    return datos


def registrar(**cambios):
    serializer = RegistroSerializer(data=datos_registro(**cambios))
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


# datos_aceptacion_privacidad()

@override_settings(VERSION_AVISO_PRIVACIDAD="3.1")
def test_version_vigente_sale_de_settings():
    assert version_vigente() == "3.1"
    assert datos_aceptacion_privacidad()["version_privacidad"] == "3.1"


def test_fecha_de_aceptacion_es_el_momento_actual():
    antes = timezone.now()
    fecha = datos_aceptacion_privacidad()["acepto_privacidad_en"]
    despues = timezone.now()
    assert antes <= fecha <= despues
    assert timezone.is_aware(fecha)


# Al registrarse

@override_settings(VERSION_AVISO_PRIVACIDAD="2026-1")
def test_el_registro_guarda_fecha_y_version_vigente():
    antes = timezone.now()
    usuario = registrar()
    usuario.refresh_from_db()

    assert usuario.version_privacidad == "2026-1"
    assert antes <= usuario.acepto_privacidad_en <= timezone.now()


def test_cada_registro_guarda_la_version_vigente_en_ese_momento():
    with override_settings(VERSION_AVISO_PRIVACIDAD="1.0"):
        primero = registrar()
    with override_settings(VERSION_AVISO_PRIVACIDAD="2.0"):
        segundo = registrar(correo="otra@ejemplo.com", telefono="353 765 4321")

    assert primero.version_privacidad == "1.0"
    assert segundo.version_privacidad == "2.0"


@override_settings(VERSION_AVISO_PRIVACIDAD="1.0")
def test_el_cliente_no_puede_mandar_su_propia_fecha_ni_version():
    hace_un_anio = (timezone.now() - timedelta(days=365)).isoformat()
    usuario = registrar(version_privacidad="0.1", acepto_privacidad_en=hace_un_anio)

    assert usuario.version_privacidad == "1.0"
    assert usuario.acepto_privacidad_en > timezone.now() - timedelta(minutes=1)


@pytest.mark.parametrize("valor", ["false", False, 0])
def test_sin_aceptar_no_se_guarda_nada(valor):
    serializer = RegistroSerializer(data=datos_registro(acepto_privacidad=valor))
    assert not serializer.is_valid()
    assert "acepto_privacidad" in serializer.errors


def test_la_respuesta_no_expone_los_datos_de_privacidad():
    serializer = RegistroSerializer(data=datos_registro())
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    for campo in ("acepto_privacidad", "acepto_privacidad_en", "version_privacidad"):
        assert campo not in serializer.data


# Revisión de la configuración al arrancar

def test_configuracion_actual_es_valida():
    assert revisar_version_aviso_privacidad() == []


@pytest.mark.parametrize("version", ["", "   "])
def test_avisa_si_la_version_esta_vacia(version):
    with override_settings(VERSION_AVISO_PRIVACIDAD=version):
        assert [e.id for e in revisar_version_aviso_privacidad()] == ["usuarios.E001"]


def test_avisa_si_la_version_no_cabe_en_la_base():
    with override_settings(VERSION_AVISO_PRIVACIDAD="v" * 21):
        assert [e.id for e in revisar_version_aviso_privacidad()] == ["usuarios.E002"]