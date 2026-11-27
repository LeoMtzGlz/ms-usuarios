"""HU-22 / ST-170: pruebas del historial de accesos que no cubrían ST-167, ST-168 ni ST-169.

Cubren los casos del plan (docs/HU-22/st-170-...md, §5) que faltaban, casi todos de punta
a punta por la API: login real → RegistroAcceso → GET /api/v1/auth/accesos/ → limpieza.
"""
import json
import threading
import time
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from usuarios import limpieza
from usuarios.limpieza import limpiar_accesos_viejos
from usuarios.models import Estado, RegistroAcceso
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
URL_HISTORIAL = "/api/v1/auth/accesos/"

UA_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
UA_ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
)
UA_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
UA_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0"


@pytest.fixture(autouse=True)
def sin_limite_de_intentos(llaves):
    """El login permite 10 intentos por minuto; cada prueba empieza con el contador en cero."""
    cache.clear()
    yield
    cache.clear()


def activo(**datos):
    return UsuarioFactory(estado=Estado.ACTIVO, **datos)


def login(api_client, usuario, password=PASSWORD_PRUEBA, **meta):
    meta.setdefault("REMOTE_ADDR", "201.141.10.5")
    return api_client.post(URL_LOGIN, {"email": usuario.email, "password": password}, format="json", **meta)


def historial(api_client, usuario, consulta=""):
    """Inicia sesión por la API y consulta el historial con ese token."""
    access = login(api_client, usuario).json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client.get(URL_HISTORIAL + consulta)


def acceso_de_hace(usuario, dias, **datos):
    registro = RegistroAcceso.objects.create(
        usuario=usuario,
        ip=datos.get("ip", "201.141.10.5"),
        dispositivo=datos.get("dispositivo", "Chrome 131 en Windows 10"),
        exitoso=datos.get("exitoso", True),
    )
    # fecha usa auto_now_add: las fechas pasadas se fabrican con update()
    RegistroAcceso.objects.filter(pk=registro.pk).update(fecha=timezone.now() - timedelta(days=dias))
    return registro


# --- §5.1 Cada login crea registro ---------------------------------------------------------

def test_p11_cada_login_por_la_api_crea_su_registro(api_client):
    """P1, P2 y P11 de punta a punta: 2 logins buenos y 1 malo → 3 registros."""
    usuario = activo()

    assert login(api_client, usuario).status_code == 200
    assert login(api_client, usuario, password="Incorrecta123").status_code == 401
    assert login(api_client, usuario).status_code == 200

    registros = RegistroAcceso.objects.filter(usuario=usuario).order_by("fecha", "id")
    exitos = list(registros.values_list("exitoso", flat=True))
    assert exitos == [True, False, True]


def test_p6_x_forwarded_for_escrito_por_el_cliente_no_cambia_la_ip(api_client, settings):
    """P6 de punta a punta: sin proxy de confianza, el encabezado se ignora."""
    settings.PROXIES_CONFIABLES = []
    usuario = activo()

    login(api_client, usuario, HTTP_X_FORWARDED_FOR="1.2.3.4")

    assert RegistroAcceso.objects.get(usuario=usuario).ip == "201.141.10.5"


@pytest.mark.parametrize(
    ("user_agent", "esperado"),
    [
        (UA_IPHONE, "Mobile Safari 17 en iOS 17.0"),
        (UA_ANDROID, "Chrome Mobile 131 en Android 14"),
        (UA_WINDOWS, "Chrome 131 en Windows 10"),
        (UA_MAC, "Firefox 133 en Mac OS X 10.15"),
    ],
)
def test_p8_dispositivo_legible_por_navegador(api_client, user_agent, esperado):
    usuario = activo()

    login(api_client, usuario, HTTP_USER_AGENT=user_agent)

    acceso = RegistroAcceso.objects.get(usuario=usuario)
    assert acceso.dispositivo == esperado
    assert acceso.user_agent == user_agent


def test_p9_user_agent_muy_largo_se_recorta_sin_romper_el_login(api_client):
    usuario = activo()
    larguisimo = UA_WINDOWS + " X" * 1000

    respuesta = login(api_client, usuario, HTTP_USER_AGENT=larguisimo)

    assert respuesta.status_code == 200
    acceso = RegistroAcceso.objects.get(usuario=usuario)
    assert len(acceso.user_agent) == 500
    assert acceso.dispositivo == "Chrome 131 en Windows 10"


@pytest.mark.parametrize("password", [PASSWORD_PRUEBA, "IntentoMalo987"])
def test_p10_el_registro_nunca_guarda_la_contrasena(api_client, password):
    usuario = activo()

    login(api_client, usuario, password=password, HTTP_USER_AGENT=UA_WINDOWS)

    guardado = json.dumps(list(RegistroAcceso.objects.filter(usuario=usuario).values()), default=str)
    assert password not in guardado


# --- §5.2 Solo veo los míos ---------------------------------------------------------------------

def test_p14_cada_quien_ve_solo_sus_accesos_despues_de_iniciar_sesion(api_client):
    """P13 y P14 de punta a punta, con dos personas iniciando sesión de verdad."""
    ana, luis = activo(), activo()
    login(api_client, luis, HTTP_USER_AGENT=UA_ANDROID)
    login(api_client, luis, HTTP_USER_AGENT=UA_ANDROID)

    datos = historial(api_client, ana).json()

    assert datos["count"] == 1  # solo el login con el que Ana consulta
    assert {r["dispositivo"] for r in datos["results"]} != {"Chrome Mobile 131 en Android 14"}


def test_intento_fallido_de_otra_persona_con_mi_correo_aparece_en_mi_historial(api_client):
    """El objetivo de HU-22: detectar accesos que no reconozco."""
    yo = activo()
    login(api_client, yo, password="AdivinandoLaClave1", REMOTE_ADDR="45.33.32.156", HTTP_USER_AGENT=UA_ANDROID)

    datos = historial(api_client, yo).json()

    intruso = [r for r in datos["results"] if not r["exitoso"]]
    assert len(intruso) == 1
    assert intruso[0]["ip"] == "45.33.32.156"
    assert intruso[0]["dispositivo"] == "Chrome Mobile 131 en Android 14"


def test_c2_el_historial_muestra_el_dispositivo_legible_del_login_real(api_client):
    usuario = activo()
    login(api_client, usuario, HTTP_USER_AGENT=UA_IPHONE)

    datos = historial(api_client, usuario).json()

    assert "Mobile Safari 17 en iOS 17.0" in [r["dispositivo"] for r in datos["results"]]
    assert all("user_agent" not in r for r in datos["results"])


def test_p16_la_segunda_pagina_trae_el_resto(api_client):
    usuario = activo()
    for dias in range(1, 25):
        acceso_de_hace(usuario, dias, ip=f"10.0.0.{dias}")

    primera = historial(api_client, usuario).json()  # + el login de la consulta = 25
    segunda = api_client.get(URL_HISTORIAL + "?page=2").json()

    assert primera["count"] == 25
    assert len(primera["results"]) == 20 and len(segunda["results"]) == 5
    assert segunda["next"] is None and segunda["previous"] is not None
    ips = [r["ip"] for r in primera["results"] + segunda["results"]]
    assert len(set(ips)) == 25  # sin repetidos entre páginas (la respuesta no expone el id)


@pytest.mark.parametrize("pagina", ["99", "abc", "0"])
def test_pagina_inexistente_responde_404_con_el_formato_estandar(api_client, pagina):
    usuario = activo()

    respuesta = historial(api_client, usuario, f"?page={pagina}")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"


# --- §5.3 Limpieza de 90 días -------------------------------------------------------------------

def test_c3_lo_que_se_limpia_ya_no_aparece_en_el_historial(api_client):
    """C2 + C3: después de limpiar, el historial solo muestra los últimos 90 días."""
    usuario = activo()
    acceso_de_hace(usuario, 120, ip="10.0.0.120")
    acceso_de_hace(usuario, 10, ip="10.0.0.10")

    limpiar_accesos_viejos()
    ips = {r["ip"] for r in historial(api_client, usuario).json()["results"]}

    assert "10.0.0.120" not in ips
    assert "10.0.0.10" in ips


@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="select_for_update(skip_locked) solo bloquea en PostgreSQL"
)
@pytest.mark.django_db(transaction=True)
def test_p24_dos_workers_a_la_vez_solo_uno_limpia(monkeypatch):
    """P24 con concurrencia real: dos conexiones a la base al mismo tiempo."""
    usuario = UsuarioFactory()
    for _ in range(3):
        acceso_de_hace(usuario, 100)

    original = limpieza.limpiar_accesos_viejos
    ejecuciones = []

    def lenta(**kwargs):
        ejecuciones.append(threading.current_thread().name)
        time.sleep(0.5)  # mantiene el candado mientras llega el segundo worker
        return original(**kwargs)

    monkeypatch.setattr(limpieza, "limpiar_accesos_viejos", lenta)
    resultados = {}

    def worker(nombre):
        try:
            resultados[nombre] = limpieza.limpiar_si_toca()
        finally:
            connection.close()

    hilos = [threading.Thread(target=worker, args=(nombre,), name=nombre) for nombre in ("w1", "w2")]
    for hilo in hilos:
        hilo.start()
        time.sleep(0.1)
    for hilo in hilos:
        hilo.join()

    assert len(ejecuciones) == 1
    assert sorted(resultados.values(), key=lambda v: v is None) == [3, None]
    assert not RegistroAcceso.objects.filter(usuario=usuario).exists()