"""Pruebas de HU-07/ST-89: lista negra de SimpleJWT con rotación de la renovación.

Igual que test_jwt_rs256.py, firman con un par de llaves temporal: no dependen de
llaves/privada.pem y corren igual en cualquier máquina y en GitHub Actions.
"""
import pytest
from django.conf import settings
from rest_framework_simplejwt import state
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .test_jwt_rs256 import _generar_par_de_llaves

pytestmark = pytest.mark.django_db


@pytest.fixture
def llaves(monkeypatch):
    """Firma y verifica con un par temporal en lugar del de llaves/."""
    privada, publica = _generar_par_de_llaves()
    backend = TokenBackend("RS256", signing_key=privada, verifying_key=publica, issuer="svc-usuarios")
    monkeypatch.setattr(state, "token_backend", backend)
    return privada, publica


def _renovar(refresh):
    """Renueva con el serializer de SimpleJWT, como lo hará el endpoint de ST-90."""
    serializer = TokenRefreshSerializer(data={"refresh": str(refresh)})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def test_la_lista_negra_esta_instalada_y_la_rotacion_activa():
    assert "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
    assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True
    assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True


def test_emitir_un_refresh_lo_registra_como_outstanding(llaves, usuario):
    refresh = RefreshToken.for_user(usuario)

    registro = OutstandingToken.objects.get(jti=refresh["jti"])
    assert registro.user == usuario


def test_renovar_entrega_refresh_nuevo_y_pone_el_anterior_en_lista_negra(llaves, usuario):
    anterior = RefreshToken.for_user(usuario)

    datos = _renovar(anterior)

    assert "access" in datos
    nuevo = RefreshToken(datos["refresh"])
    assert nuevo["jti"] != anterior["jti"]
    assert BlacklistedToken.objects.filter(token__jti=anterior["jti"]).exists()
    assert OutstandingToken.objects.filter(jti=nuevo["jti"]).exists()
    assert not BlacklistedToken.objects.filter(token__jti=nuevo["jti"]).exists()


def test_renovar_otra_vez_con_el_refresh_anterior_falla(llaves, usuario):
    anterior = RefreshToken.for_user(usuario)
    _renovar(anterior)

    with pytest.raises(TokenError):
        _renovar(anterior)


def test_un_refresh_en_lista_negra_a_mano_ya_no_sirve(llaves, usuario):
    refresh = RefreshToken.for_user(usuario)
    refresh.blacklist()

    with pytest.raises(TokenError):
        _renovar(refresh)
