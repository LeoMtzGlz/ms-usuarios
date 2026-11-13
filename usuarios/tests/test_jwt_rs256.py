"""Pruebas de T-04/ST-21: SimpleJWT firma con RS256, acceso de 15 min y renovación de 7 días.

No dependen de llaves/privada.pem: cada prueba genera un par temporal, así corren igual
en cualquier máquina y en GitHub Actions.
"""
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt import state
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.tokens import RefreshToken

from config.settings import leer_llave

from .factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _generar_par_de_llaves():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privada_pem = privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    publica_pem = (
        privada.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return privada_pem, publica_pem


@pytest.fixture
def llaves(monkeypatch):
    """Firma y verifica con un par temporal en lugar del de llaves/."""
    privada, publica = _generar_par_de_llaves()
    backend = TokenBackend("RS256", signing_key=privada, verifying_key=publica, issuer="svc-usuarios")
    monkeypatch.setattr(state, "token_backend", backend)
    return privada, publica


def test_configuracion_de_simple_jwt():
    assert settings.SIMPLE_JWT["ALGORITHM"] == "RS256"
    assert settings.SIMPLE_JWT["ISSUER"] == "svc-usuarios"
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=15)
    assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(days=7)


def test_jwt_es_la_primera_clase_de_autenticacion():
    clases = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    assert clases[0] == "rest_framework_simplejwt.authentication.JWTAuthentication"


def test_el_token_se_firma_con_rs256_y_lleva_el_emisor(llaves):
    acceso = str(RefreshToken.for_user(UsuarioFactory()).access_token)

    assert jwt.get_unverified_header(acceso)["alg"] == "RS256"
    assert jwt.decode(acceso, options={"verify_signature": False})["iss"] == "svc-usuarios"


def test_el_acceso_dura_15_minutos_y_la_renovacion_7_dias(llaves):
    renovacion = RefreshToken.for_user(UsuarioFactory())
    acceso = renovacion.access_token

    assert acceso["exp"] - acceso["iat"] == 15 * 60
    assert renovacion["exp"] - renovacion["iat"] == 7 * 24 * 60 * 60


def test_otro_servicio_valida_el_token_solo_con_la_llave_publica(llaves):
    _, publica = llaves
    usuario = UsuarioFactory()
    acceso = str(RefreshToken.for_user(usuario).access_token)

    datos = TokenBackend("RS256", verifying_key=publica, issuer="svc-usuarios").decode(acceso)
    assert datos["token_type"] == "access"
    assert datos["user_id"] == str(usuario.id)


def test_un_token_firmado_con_otra_llave_se_rechaza(llaves):
    _, publica = llaves
    otra_privada, _ = _generar_par_de_llaves()
    falso = TokenBackend("RS256", signing_key=otra_privada, issuer="svc-usuarios").encode({"user_id": "x"})

    with pytest.raises(TokenBackendError):
        TokenBackend("RS256", verifying_key=publica, issuer="svc-usuarios").decode(falso)


def test_un_token_invalido_responde_401_con_el_formato_del_equipo(llaves):
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION="Bearer esto-no-es-un-token")

    respuesta = cliente.get("/api/schema/", {"format": "json"})

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"
    assert respuesta["WWW-Authenticate"].startswith("Bearer")


def test_leer_llave_acepta_ruta_o_contenido(tmp_path, monkeypatch):
    archivo = tmp_path / "publica.pem"
    archivo.write_text("-----BEGIN PUBLIC KEY-----\nABC\n-----END PUBLIC KEY-----\n")

    monkeypatch.setenv("JWT_LLAVE_PUBLICA", str(archivo))
    assert leer_llave("JWT_LLAVE_PUBLICA", "llaves/publica.pem").startswith("-----BEGIN PUBLIC KEY-----")

    monkeypatch.setenv("JWT_LLAVE_PUBLICA", "-----BEGIN PUBLIC KEY-----\\nABC\\nEND PUBLIC KEY-----")
    assert leer_llave("JWT_LLAVE_PUBLICA", "llaves/publica.pem").splitlines()[1] == "ABC"

    monkeypatch.setenv("JWT_LLAVE_PUBLICA", str(tmp_path / "no-existe.pem"))
    assert leer_llave("JWT_LLAVE_PUBLICA", "llaves/publica.pem") == ""