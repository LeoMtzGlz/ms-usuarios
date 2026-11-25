"""Pruebas de t-22/st-168 (HU-22): GET /api/v1/auth/accesos/ · paginado y solo mis accesos."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.models import RegistroAcceso
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory
from usuarios.tokens import CustomTokenObtainPairSerializer

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/accesos/"


def _acceso(usuario, minutos_atras=0, **datos):
    acceso = RegistroAcceso.objects.create(
        usuario=usuario,
        ip=datos.get("ip", "201.141.10.5"),
        dispositivo=datos.get("dispositivo", "Chrome 131 en Windows 10"),
        user_agent=datos.get("user_agent", "Mozilla/5.0 (Windows NT 10.0)"),
        exitoso=datos.get("exitoso", True),
    )
    # fecha usa auto_now_add: se ajusta con update() para fabricar fechas pasadas
    RegistroAcceso.objects.filter(pk=acceso.pk).update(fecha=timezone.now() - timedelta(minutes=minutos_atras))
    return acceso


def _con_sesion(api_client, usuario, **claims):
    acceso = RefreshToken.for_user(usuario).access_token
    for nombre, valor in claims.items():
        acceso[nombre] = valor
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api_client


def test_sin_token_responde_401(api_client, llaves):
    respuesta = api_client.get(URL)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"


def test_solo_veo_mis_accesos(api_client, llaves):
    yo, otro = UsuarioFactory(), UsuarioFactory()
    for _ in range(3):
        _acceso(yo)
    for _ in range(4):
        _acceso(otro, ip="10.9.9.9")

    datos = _con_sesion(api_client, yo).get(URL).json()

    assert datos["count"] == 3
    assert all(r["ip"] == "201.141.10.5" for r in datos["results"])


def test_parametro_de_otro_usuario_se_ignora(api_client, llaves):
    yo, otro = UsuarioFactory(), UsuarioFactory()
    _acceso(yo)
    _acceso(otro)

    datos = _con_sesion(api_client, yo).get(URL, {"usuario": str(otro.id), "usuario_id": str(otro.id)}).json()

    assert datos["count"] == 1


def test_pagina_de_20_mas_recientes_primero(api_client, llaves):
    yo = UsuarioFactory()
    for minutos in range(25):
        _acceso(yo, minutos_atras=minutos)

    cliente = _con_sesion(api_client, yo)
    datos = cliente.get(URL).json()

    fechas = [r["fecha"] for r in datos["results"]]
    assert datos["count"] == 25
    assert len(fechas) == 20
    assert fechas == sorted(fechas, reverse=True)
    assert datos["next"] is not None
    assert len(cliente.get(datos["next"]).json()["results"]) == 5


def test_no_se_pueden_pedir_mas_de_20(api_client, llaves):
    yo = UsuarioFactory()
    for minutos in range(25):
        _acceso(yo, minutos_atras=minutos)

    datos = _con_sesion(api_client, yo).get(URL, {"page_size": 1000}).json()

    assert len(datos["results"]) == 20


def test_campos_de_la_respuesta(api_client, llaves):
    yo = UsuarioFactory()
    _acceso(yo, exitoso=False, dispositivo="Mobile Safari 17 en iOS 17.1")

    registro = _con_sesion(api_client, yo).get(URL).json()["results"][0]

    assert set(registro) == {"fecha", "ip", "dispositivo", "exitoso"}
    assert registro["dispositivo"] == "Mobile Safari 17 en iOS 17.1"
    assert registro["exitoso"] is False


def test_sin_registros_devuelve_lista_vacia(api_client, llaves):
    datos = _con_sesion(api_client, UsuarioFactory()).get(URL).json()

    assert datos["count"] == 0
    assert datos["results"] == []


def test_con_contrasena_temporal_responde_403(api_client, llaves):
    respuesta = _con_sesion(api_client, UsuarioFactory(), debe_cambiar_password=True).get(URL)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "debe_cambiar_password"


def test_el_login_real_aparece_en_mi_historial(api_client, llaves):
    yo = UsuarioFactory()
    request = APIRequestFactory().post("/api/v1/auth/login/", REMOTE_ADDR="201.141.10.5")
    serializer = CustomTokenObtainPairSerializer(
        data={"email": yo.email, "password": PASSWORD_PRUEBA}, context={"request": request}
    )
    assert serializer.is_valid(), serializer.errors

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {serializer.validated_data['access']}")
    registro = api_client.get(URL).json()["results"][0]

    assert registro["ip"] == "201.141.10.5"
    assert registro["exitoso"] is True