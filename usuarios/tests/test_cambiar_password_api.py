
"""HU-11 / ST-114: pruebas de emisión de tokens al cambiar la contraseña."""

import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from usuarios.tests.factories import PASSWORD_PRUEBA


pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"
URL_CAMBIAR_PASSWORD = "/api/v1/auth/cambiar-password/"
URL_RENOVAR = "/api/v1/auth/token/renovar/"
URL_PROTEGIDO = "/api/v1/auth/privacidad/aceptar/"

NUEVA_PASSWORD = "ClaveDistinta#2026Z"


def iniciar_sesion(api_client, usuario):
    respuesta = api_client.post(
        URL_LOGIN,
        {
            "email": usuario.email,
            "password": PASSWORD_PRUEBA,
            "recordarme": False,
        },
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data
    return respuesta.data


def cambiar_password(api_client, access, password_actual=PASSWORD_PRUEBA):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access}"
    )

    return api_client.post(
        URL_CAMBIAR_PASSWORD,
        {
            "password_actual": password_actual,
            "password_nueva": NUEVA_PASSWORD,
            "password_confirmacion": NUEVA_PASSWORD,
        },
        format="json",
    )


def test_emite_tokens_nuevos_con_claims_actualizados(
    api_client, usuario, llaves
):
    """ST-114: emitir access y refresh con los claims actuales."""

    login = iniciar_sesion(api_client, usuario)
    version_anterior = usuario.token_version

    respuesta = cambiar_password(
        api_client,
        login["access"],
    )

    assert respuesta.status_code == 200, respuesta.data
    assert respuesta.data["mensaje"] == (
        "Contraseña actualizada correctamente."
    )
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data

    usuario.refresh_from_db()

    access = AccessToken(respuesta.data["access"])
    refresh = RefreshToken(respuesta.data["refresh"])

    # La versión debe incrementarse.
    assert usuario.token_version == version_anterior + 1

    # La contraseña ya es definitiva.
    assert usuario.debe_cambiar_password is False

    # Ambos tokens deben contener los claims personalizados.
    for token in (access, refresh):
        assert token["user_id"] == str(usuario.pk)
        assert token["rol"] == usuario.rol
        assert token["email_verificado"] == usuario.email_verificado
        assert token["token_version"] == usuario.token_version
        assert token["debe_cambiar_password"] is False
        assert token["zona_id"] == (
            str(usuario.zona_id) if usuario.zona_id else None
        )

    # La contraseña anterior deja de funcionar.
    assert not usuario.check_password(PASSWORD_PRUEBA)

    # La nueva contraseña funciona.
    assert usuario.check_password(NUEVA_PASSWORD)


def test_el_nuevo_access_permite_acceder_a_endpoint_protegido(
    api_client, usuario, llaves
):
    """ST-114: el usuario conserva su sesión en el dispositivo actual."""

    login = iniciar_sesion(api_client, usuario)

    cambio = cambiar_password(
        api_client,
        login["access"],
    )

    assert cambio.status_code == 200, cambio.data

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {cambio.data['access']}"
    )

    respuesta = api_client.post(
        URL_PROTEGIDO,
        {},
        format="json",
    )

    assert respuesta.status_code == 200, respuesta.data


def test_rechaza_refresh_anterior_y_acepta_refresh_nuevo(
    api_client, usuario, llaves
):
    """ST-114: comprobar la renovación con los tokens emitidos."""

    login = iniciar_sesion(api_client, usuario)
    refresh_anterior = login["refresh"]

    cambio = cambiar_password(
        api_client,
        login["access"],
    )

    assert cambio.status_code == 200, cambio.data

    # El refresh anterior tiene una versión desactualizada.
    respuesta_anterior = api_client.post(
        URL_RENOVAR,
        {"refresh": refresh_anterior},
        format="json",
    )

    assert respuesta_anterior.status_code == 401

    # El refresh nuevo debe permitir renovar la sesión.
    respuesta_nueva = api_client.post(
        URL_RENOVAR,
        {"refresh": cambio.data["refresh"]},
        format="json",
    )

    assert respuesta_nueva.status_code == 200, respuesta_nueva.data
    assert "access" in respuesta_nueva.data
    assert "refresh" in respuesta_nueva.data

    nuevo_access = AccessToken(respuesta_nueva.data["access"])
    assert nuevo_access["token_version"] == usuario.token_version + 1


def test_rechaza_cambio_con_contrasena_actual_incorrecta(
    api_client, usuario, llaves
):
    """ST-114: no cambiar la contraseña si la actual es incorrecta."""

    login = iniciar_sesion(api_client, usuario)
    version_anterior = usuario.token_version

    respuesta = cambiar_password(
        api_client,
        login["access"],
        password_actual="ContrasenaIncorrecta2026!",
    )

    assert respuesta.status_code == 400

    usuario.refresh_from_db()

    assert usuario.token_version == version_anterior
    assert usuario.check_password(PASSWORD_PRUEBA)
    assert "access" not in respuesta.data
    assert "refresh" not in respuesta.data


def test_rechaza_solicitud_sin_autenticacion(
    api_client, usuario, llaves
):
    """ST-114: el cambio de contraseña requiere autenticación."""

    respuesta = api_client.post(
        URL_CAMBIAR_PASSWORD,
        {
            "password_actual": PASSWORD_PRUEBA,
            "password_nueva": NUEVA_PASSWORD,
            "password_confirmacion": NUEVA_PASSWORD,
        },
        format="json",
    )

    assert respuesta.status_code == 401


def test_rechaza_contrasena_nueva_que_no_cumple_la_politica(
    api_client, usuario, llaves
):
    """ST-114: no emitir tokens cuando la nueva contraseña es inválida."""

    login = iniciar_sesion(api_client, usuario)
    version_anterior = usuario.token_version

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {login['access']}"
    )

    respuesta = api_client.post(
        URL_CAMBIAR_PASSWORD,
        {
            "password_actual": PASSWORD_PRUEBA,
            "password_nueva": "123",
            "password_confirmacion": "123",
        },
        format="json",
    )

    assert respuesta.status_code == 400

    usuario.refresh_from_db()

    assert usuario.token_version == version_anterior
    assert usuario.check_password(PASSWORD_PRUEBA)
    assert "access" not in respuesta.data
    assert "refresh" not in respuesta.data
