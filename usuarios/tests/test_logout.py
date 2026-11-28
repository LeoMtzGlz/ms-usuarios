"""Pruebas de HU-08/ST-94: cierre de sesión mediante refresh JWT."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from usuarios.tests.factories import UsuarioFactory
from usuarios.tokens import CustomTokenObtainPairSerializer

pytestmark = pytest.mark.django_db

URL_LOGOUT = "/api/v1/auth/logout/"
URL_RENOVAR = "/api/v1/auth/token/renovar/"


def _iniciar_sesion(api_client, usuario):
    """Genera un refresh y deja el access del mismo usuario en el cliente."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return refresh


def _esta_en_lista_negra(refresh):
    return BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()


def test_logout_invalida_refresh_token(api_client, usuario, llaves):
    """Cerrar sesión debe revocar el refresh recibido."""
    refresh = _iniciar_sesion(api_client, usuario)

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert respuesta.status_code == 200, respuesta.data
    assert respuesta.data["mensaje"] == "Sesión cerrada correctamente."
    assert _esta_en_lista_negra(refresh)

    # Un refresh revocado no debe permitir renovar la sesión.
    api_client.credentials()
    renovacion = api_client.post(URL_RENOVAR, {"refresh": str(refresh)}, format="json")

    assert renovacion.status_code == 401
    assert renovacion.json()["codigo"] == "token_invalido"


def test_logout_dos_veces_no_falla(api_client, usuario, llaves):
    """HU-08: cerrar sesión dos veces con el mismo refresh no da error."""
    refresh = _iniciar_sesion(api_client, usuario)

    primera = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")
    segunda = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert primera.status_code == 200, primera.data
    assert segunda.status_code == 200, segunda.data
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).count() == 1


def test_logout_exige_access_token(api_client, usuario, llaves):
    """ST-94: el logout requiere un access válido."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "no_autenticado"
    assert not _esta_en_lista_negra(refresh)


def test_logout_rechaza_access_vencido(api_client, usuario, llaves):
    """Un access vencido no autoriza el cierre de sesión."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    access = refresh.access_token
    access.set_exp(
        from_time=timezone.now() - timedelta(minutes=2),
        lifetime=timedelta(minutes=1),
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert respuesta.status_code == 401
    assert not _esta_en_lista_negra(refresh)


def test_logout_rechaza_refresh_de_otro_usuario(api_client, usuario, llaves):
    """HU-08: un refresh de otro usuario responde 403 y no se revoca."""
    _iniciar_sesion(api_client, usuario)
    refresh_ajeno = CustomTokenObtainPairSerializer.get_token(UsuarioFactory())

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh_ajeno)}, format="json")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"
    assert not _esta_en_lista_negra(refresh_ajeno)


def test_logout_rechaza_refresh_invalido(api_client, usuario, llaves):
    """El logout debe rechazar un refresh malformado."""
    _iniciar_sesion(api_client, usuario)

    respuesta = api_client.post(URL_LOGOUT, {"refresh": "token-invalido"}, format="json")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_refresh_vencido(api_client, usuario, llaves):
    """El logout debe rechazar un refresh expirado."""
    _iniciar_sesion(api_client, usuario)
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    refresh.set_exp(
        from_time=timezone.now() - timedelta(minutes=2),
        lifetime=timedelta(minutes=1),
    )

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_access_como_refresh(api_client, usuario, llaves):
    """Un access token no sirve como refresh para cerrar sesión."""
    refresh = _iniciar_sesion(api_client, usuario)

    respuesta = api_client.post(
        URL_LOGOUT, {"refresh": str(refresh.access_token)}, format="json"
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"


def test_logout_rechaza_solicitud_sin_refresh(api_client, usuario, llaves):
    """El endpoint debe rechazar solicitudes sin refresh."""
    _iniciar_sesion(api_client, usuario)

    respuesta = api_client.post(URL_LOGOUT, {}, format="json")

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert "refresh" in respuesta.json()["campos"]


def test_logout_funciona_con_contrasena_temporal(api_client, llaves):
    """Un usuario con contraseña temporal también puede cerrar sesión."""
    usuario = UsuarioFactory(debe_cambiar_password=True)
    refresh = _iniciar_sesion(api_client, usuario)

    respuesta = api_client.post(URL_LOGOUT, {"refresh": str(refresh)}, format="json")

    assert respuesta.status_code == 200, respuesta.data
    assert _esta_en_lista_negra(refresh)
