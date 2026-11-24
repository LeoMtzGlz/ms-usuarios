
"""Prueba funcional temporal de HU-07 / ST-90."""

import pytest
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework.test import APIClient

from django.db import connections

from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from uuid import uuid4


pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
URL_RENOVAR = "/api/v1/auth/token/renovar/"


def test_renovacion_correcta(api_client, usuario, llaves):
    # Iniciar sesión sin "recordarme": refresh de un día.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200

    refresh_anterior = login.data["refresh"]

    # Renovar la sesión.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data

    refresh_nuevo = RefreshToken(respuesta.data["refresh"])

    # El refresh nuevo debe tener otro identificador.
    assert refresh_nuevo["jti"] != RefreshToken(
        refresh_anterior, verify=False
    )["jti"]

    # Debe conservar la duración de un día.
    duracion = refresh_nuevo["exp"] - refresh_nuevo["iat"]
    assert abs(duracion - 86400) <= 1
    assert refresh_nuevo["recordarme"] is False

    # El refresh anterior no debe poder reutilizarse.
    reutilizacion = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert reutilizacion.status_code == 401


def test_rechaza_refresh_con_token_version_anterior(api_client, usuario, llaves):
    # Iniciar sesión y obtener un refresh válido.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # t-07/st-90: Simular la invalidación de las sesiones del usuario.
    usuario.token_version += 1
    usuario.save(update_fields=["token_version"])

    # Intentar renovar utilizando el refresh emitido anteriormente.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"
    assert "access" not in respuesta.json()
    assert "refresh" not in respuesta.json()


def test_rechaza_refresh_de_usuario_inactivo(api_client, usuario, llaves):
    # Obtener un refresh válido mientras el usuario está activo.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # t-07/st-90: Simular que el administrador desactiva la cuenta.
    usuario.estado = "inactivo"
    usuario.is_active = False
    usuario.save(update_fields=["estado", "is_active"])

    # Intentar renovar con el refresh emitido anteriormente.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"
    assert "access" not in respuesta.json()
    assert "refresh" not in respuesta.json()


def test_renovacion_actualiza_claims(api_client, usuario, llaves):
    # Obtener un refresh antes de cambiar los datos del usuario.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # t-07/st-90: Cambiar datos sin invalidar la sesión.
    rol_original = usuario.rol
    usuario.rol = next(
        valor for valor, _ in usuario._meta.get_field("rol").choices
        if valor != rol_original
    )
    usuario.email_verificado = not usuario.email_verificado
    usuario.save(update_fields=["rol", "email_verificado"])

    # Renovar utilizando el refresh emitido antes del cambio.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data

    nuevo_access = AccessToken(respuesta.data["access"])
    nuevo_refresh = RefreshToken(respuesta.data["refresh"])

    # Ambos tokens deben contener los datos actuales.
    for token in (nuevo_access, nuevo_refresh):
        assert token["rol"] == usuario.rol
        assert token["email_verificado"] == usuario.email_verificado
        assert token["token_version"] == usuario.token_version


def test_renovacion_con_recordarme_conserva_siete_dias(api_client, usuario, llaves):
    # t-07/st-90: Iniciar sesión con recordarme activado.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": True,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # Renovar la sesión.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data

    nuevo_refresh = RefreshToken(respuesta.data["refresh"])

    # Verificar que mantiene el valor de recordarme.
    assert nuevo_refresh["recordarme"] is True

    # La duración debe seguir siendo de siete días.
    duracion = nuevo_refresh["exp"] - nuevo_refresh["iat"]
    assert abs(duracion - 7 * 24 * 60 * 60) <= 1


def test_rechaza_refresh_invalido(api_client, llaves):
    """HU-07 / ST-90: Un refresh inválido no debe renovar la sesión."""

    # t-07/st-90: Enviar un token que no tiene un formato JWT válido.
    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": "token-invalido-de-prueba"},
        format="json",
    )

    # La API debe rechazar la renovación.
    assert respuesta.status_code == 401

    # Verificar el formato estándar de errores.
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "mensaje" in cuerpo
    assert "campos" in cuerpo

    # No deben entregarse tokens.
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rechaza_refresh_de_usuario_inexistente(api_client, usuario, llaves):
    """HU-07 / ST-90: No renovar tokens de usuarios inexistentes."""

    # Obtener un refresh válido y correctamente firmado.
    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200

    # t-07/st-90: Simular un token firmado de una cuenta inexistente.
    refresh = RefreshToken(login.data["refresh"])
    refresh["user_id"] = str(uuid4())

    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rechaza_refresh_con_user_id_invalido(api_client, usuario, llaves):
    """HU-07 / ST-90: Un user_id malformado no debe provocar HTTP 500."""

    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200

    # t-07/st-90: Crear un refresh firmado con un UUID inválido.
    refresh = RefreshToken(login.data["refresh"])
    refresh["user_id"] = "usuario-invalido"

    # Permitir inspeccionar la respuesta aunque el servidor genere HTTP 500.
    api_client.raise_request_exception = False

    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh)},
        format="json",
    )

    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rechaza_refresh_de_usuario_pendiente(api_client, usuario, llaves):
    """HU-07 / ST-90: Una cuenta pendiente no puede renovar su sesión."""

    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # t-07/st-90: Cambiar únicamente el estado de la cuenta.
    usuario.estado = "pendiente"
    usuario.save(update_fields=["estado"])

    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta.status_code == 401

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "token_invalido"
    assert "access" not in cuerpo
    assert "refresh" not in cuerpo


def test_rotacion_actualiza_lista_negra_y_tokens_pendientes(
    api_client, usuario, llaves
):
    """HU-07 / ST-90: Registrar el nuevo refresh e invalidar el anterior."""

    login = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = RefreshToken(login.data["refresh"])

    respuesta = api_client.post(
        URL_RENOVAR,
        {"refresh": str(refresh_anterior)},
        format="json",
    )

    assert respuesta.status_code == 200

    refresh_nuevo = RefreshToken(respuesta.data["refresh"])

    # t-07/st-90: El token anterior debe estar en la lista negra.
    registro_anterior = OutstandingToken.objects.get(
        jti=refresh_anterior["jti"]
    )

    assert BlacklistedToken.objects.filter(
        token=registro_anterior
    ).exists()

    # El nuevo refresh debe estar registrado.
    registro_nuevo = OutstandingToken.objects.get(
        jti=refresh_nuevo["jti"]
    )

    assert registro_nuevo.user_id == usuario.id

    # El nuevo refresh todavía no debe estar bloqueado.
    assert not BlacklistedToken.objects.filter(
        token=registro_nuevo
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_dos_renovaciones_simultaneas_no_reutilizan_refresh(
    llaves,
):
    """HU-07 / ST-90: Un refresh no debe renovarse dos veces."""

    # t-07/st-90: Crear el usuario en una transacción confirmada.
    usuario = UsuarioFactory()
    cliente_login = APIClient()

    login = cliente_login.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert login.status_code == 200
    refresh_anterior = login.data["refresh"]

    # Sincronizar el inicio de ambas peticiones.
    barrera = Barrier(2)

    def renovar():
        # Cada hilo utiliza su propia conexión de PostgreSQL.
        connections.close_all()
        try:
            cliente = APIClient()
            barrera.wait(timeout=10)

            respuesta = cliente.post(
                URL_RENOVAR,
                {"refresh": refresh_anterior},
                format="json",
            )

            return respuesta.status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(renovar)
        futuro_b = executor.submit(renovar)

        resultados = [
            futuro_a.result(timeout=20),
            futuro_b.result(timeout=20),
        ]

    # Solo una petición debe poder renovar el refresh anterior.
    assert sorted(resultados) == [200, 401]
