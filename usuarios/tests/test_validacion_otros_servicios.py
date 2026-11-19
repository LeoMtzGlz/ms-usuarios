"""Pruebas de T-14/ST-137: cómo valida otro microservicio los tokens de svc-usuarios.

Simulan un servicio externo (catálogo, pedidos...) configurado como dice
docs/T-14/ST-136-guia-integracion.md: verifica la firma solo con la llave pública,
sin consultar la base de svc-usuarios, y exige el claim rol.
"""
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt import state
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import UsuarioFactory


class JWTDeUsuarios(JWTStatelessUserAuthentication):
    """La clase de la guía (ST-136): stateless y exige el claim rol."""

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if not token.get("rol"):
            raise InvalidToken("El token no trae rol.")
        return token


class VistaDeOtroServicio(APIView):
    authentication_classes = [JWTDeUsuarios]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"id": str(request.user.id), "rol": request.auth.get("rol")})


@pytest.fixture
def emisor(llaves, monkeypatch):
    """Firma como svc-usuarios (llave privada) y deja al 'otro servicio' solo con la pública."""
    privada, publica = llaves
    monkeypatch.setattr(state, "token_backend", TokenBackend("RS256", verifying_key=publica, issuer="svc-usuarios"))
    return TokenBackend("RS256", signing_key=privada, issuer="svc-usuarios")


def _datos(**cambios):
    ahora = int(time.time())
    datos = {
        "token_type": "access",
        "iat": ahora,
        "exp": ahora + 15 * 60,
        "jti": "prueba",
        "user_id": "usuario-123",
        "rol": "cliente",
    }
    datos.update(cambios)
    return {clave: valor for clave, valor in datos.items() if valor is not None}


def _llamar(token=None):
    encabezados = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    respuesta = VistaDeOtroServicio.as_view()(APIRequestFactory().get("/api/mis-pedidos/", **encabezados))
    respuesta.render()
    return respuesta


def _otra_llave():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()


def test_token_valido_entrega_id_y_rol(emisor):
    respuesta = _llamar(emisor.encode(_datos()))

    assert respuesta.status_code == 200
    assert respuesta.data == {"id": "usuario-123", "rol": "cliente"}


def test_token_firmado_con_otra_llave_responde_401(emisor):
    falso = TokenBackend("RS256", signing_key=_otra_llave(), issuer="svc-usuarios").encode(_datos())

    respuesta = _llamar(falso)

    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "token_invalido"


def test_token_vencido_responde_401(emisor):
    ahora = int(time.time())
    vencido = emisor.encode(_datos(iat=ahora - 16 * 60, exp=ahora - 60))

    respuesta = _llamar(vencido)

    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "token_invalido"


def test_token_sin_rol_responde_401(emisor):
    respuesta = _llamar(emisor.encode(_datos(rol=None)))

    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "token_invalido"


def test_token_de_otro_emisor_responde_401(emisor, llaves):
    privada, _ = llaves
    ajeno = TokenBackend("RS256", signing_key=privada, issuer="otro-servicio").encode(_datos())

    assert _llamar(ajeno).status_code == 401


def test_token_de_renovacion_no_sirve_como_acceso(emisor):
    assert _llamar(emisor.encode(_datos(token_type="refresh"))).status_code == 401


def test_sin_encabezado_responde_401(emisor):
    respuesta = _llamar()

    assert respuesta.status_code == 401
    assert respuesta["WWW-Authenticate"].startswith("Bearer")


@pytest.mark.django_db
def test_token_real_de_svc_usuarios_se_valida_solo_con_la_llave_publica(llaves, monkeypatch):
    _, publica = llaves
    usuario = UsuarioFactory()
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = "administrador"  # el login de HU-05 agregará este claim
    token = str(acceso)

    monkeypatch.setattr(state, "token_backend", TokenBackend("RS256", verifying_key=publica, issuer="svc-usuarios"))
    respuesta = _llamar(token)

    assert respuesta.status_code == 200
    assert respuesta.data == {"id": str(usuario.id), "rol": "administrador"}