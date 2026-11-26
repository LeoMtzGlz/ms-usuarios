"""HU-33 / ST-219: POST /api/v1/auth/google/ (verificar el ID token y crear o vincular la cuenta)."""
import datetime
import time
from unittest import mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt
from google.auth import exceptions as google_exceptions
from google.auth import jwt as google_jwt
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from comun.roles import Rol
from usuarios.models import Dispositivo2FA, Estado, RegistroAcceso, Usuario
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/google/"
CLIENT_ID = "123456789012-prueba.apps.googleusercontent.com"
VERIFICAR = "usuarios.login_google.id_token.verify_oauth2_token"


@pytest.fixture(autouse=True)
def google_configurado(settings, llaves):
    settings.GOOGLE_CLIENT_ID = CLIENT_ID


def datos_google(**cambios):
    datos = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "110169484474386276334",
        "email": "maria.google@gmail.com",
        "email_verified": True,
        "given_name": "María",
        "family_name": "Hernández",
    }
    datos.update(cambios)
    return datos


def login_google(api_client, info=None, **cuerpo):
    cuerpo.setdefault("id_token", "token-de-prueba")
    with mock.patch(VERIFICAR, return_value=info or datos_google()):
        return api_client.post(URL, cuerpo, format="json")


# --- Cuenta nueva --------------------------------------------------------------------------

def test_correo_nuevo_crea_un_cliente_verificado_sin_contrasena(api_client):
    respuesta = login_google(api_client)

    assert respuesta.status_code == 200
    assert respuesta.json()["cuenta_nueva"] is True
    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert usuario.rol == Rol.CLIENTE
    assert usuario.estado == Estado.ACTIVO and usuario.is_active
    assert usuario.email_verificado is True
    assert usuario.has_usable_password() is False
    assert (usuario.first_name, usuario.last_name) == ("María", "Hernández")


def test_emite_los_mismos_jwt_que_el_login(api_client):
    cuerpo = login_google(api_client).json()

    access = AccessToken(cuerpo["access"])
    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert access["user_id"] == str(usuario.pk)
    for claim in ("rol", "email_verificado", "token_version", "debe_cambiar_password", "zona_id"):
        assert claim in access
    assert RefreshToken(cuerpo["refresh"])["recordarme"] is False
    assert cuerpo["usuario"] == {"id": str(usuario.pk), "nombre": "María", "email": usuario.email, "rol": "cliente"}


def test_recordarme_alarga_el_refresh_a_7_dias(api_client):
    cuerpo = login_google(api_client, recordarme=True).json()

    refresh = RefreshToken(cuerpo["refresh"])
    dias = (refresh["exp"] - refresh["iat"]) / 86400
    assert refresh["recordarme"] is True
    assert round(dias) == 7


def test_guarda_la_aceptacion_de_privacidad_si_la_envia(api_client):
    login_google(api_client, acepto_privacidad=True)

    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert usuario.acepto_privacidad_en is not None
    assert usuario.version_privacidad


def test_sin_aceptar_privacidad_la_cuenta_se_crea_sin_fecha(api_client):
    login_google(api_client)

    assert Usuario.objects.get(email="maria.google@gmail.com").acepto_privacidad_en is None


def test_sin_nombre_en_google_se_crea_igual(api_client):
    info = datos_google()
    del info["given_name"], info["family_name"]
    assert login_google(api_client, info).status_code == 200


# --- Cuenta existente: se vincula -----------------------------------------------------------

def test_correo_existente_se_vincula_sin_crear_otra_cuenta(api_client):
    existente = UsuarioFactory(email="maria.google@gmail.com", estado=Estado.ACTIVO)
    respuesta = login_google(api_client, datos_google(email="MARIA.Google@gmail.com"))

    assert respuesta.status_code == 200
    assert respuesta.json()["cuenta_nueva"] is False
    assert Usuario.objects.filter(email__iexact="maria.google@gmail.com").count() == 1
    assert AccessToken(respuesta.json()["access"])["user_id"] == str(existente.pk)


def test_vincular_no_toca_la_contrasena_ni_el_rol(api_client):
    UsuarioFactory(email="maria.google@gmail.com", estado=Estado.ACTIVO, rol=Rol.OPERATIVO)
    login_google(api_client)

    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert usuario.check_password(PASSWORD_PRUEBA)  # sigue pudiendo entrar con contraseña
    assert usuario.rol == Rol.OPERATIVO


def test_cuenta_pendiente_se_activa_porque_google_verifico_el_correo(api_client):
    UsuarioFactory(email="maria.google@gmail.com", estado=Estado.PENDIENTE, email_verificado=False)
    respuesta = login_google(api_client)

    assert respuesta.status_code == 200
    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert usuario.estado == Estado.ACTIVO
    assert usuario.email_verificado is True


def test_cuenta_inactiva_no_entra(api_client):
    usuario = UsuarioFactory(email="maria.google@gmail.com", estado=Estado.ACTIVO)
    usuario.cambiar_estado(Estado.INACTIVO)
    respuesta = login_google(api_client)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "cuenta_inactiva"
    assert RegistroAcceso.objects.filter(usuario=usuario, exitoso=False).count() == 1


def test_con_2fa_activo_pide_el_segundo_paso(api_client):
    usuario = UsuarioFactory(email="maria.google@gmail.com", estado=Estado.ACTIVO)
    Dispositivo2FA.objects.create(usuario=usuario, secreto_cifrado="x", confirmado=True)
    cuerpo = login_google(api_client).json()

    assert cuerpo["requiere_2fa"] is True
    assert cuerpo["token_temporal"]
    assert "access" not in cuerpo and "refresh" not in cuerpo


def test_registra_el_acceso_exitoso(api_client):
    login_google(api_client)

    usuario = Usuario.objects.get(email="maria.google@gmail.com")
    assert RegistroAcceso.objects.filter(usuario=usuario, exitoso=True).count() == 1


# --- Errores --------------------------------------------------------------------------------

def test_token_rechazado_por_google_responde_401(api_client):
    with mock.patch(VERIFICAR, side_effect=ValueError("Token expired")):
        respuesta = api_client.post(URL, {"id_token": "malo"}, format="json")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_google_invalido"
    assert not Usuario.objects.exists()


def test_emisor_incorrecto_responde_401(api_client):
    with mock.patch(VERIFICAR, side_effect=google_exceptions.GoogleAuthError("Wrong issuer")):
        respuesta = api_client.post(URL, {"id_token": "malo"}, format="json")

    assert respuesta.json()["codigo"] == "token_google_invalido"


@pytest.mark.parametrize("cambio", [{"email_verified": False}, {"email_verified": "true"}, {"email": ""}])
def test_correo_no_verificado_por_google_responde_401(api_client, cambio):
    respuesta = login_google(api_client, datos_google(**cambio))

    assert respuesta.status_code == 401
    assert not Usuario.objects.exists()


def test_sin_google_client_id_no_verifica_nada(api_client, settings):
    settings.GOOGLE_CLIENT_ID = ""
    with mock.patch(VERIFICAR) as verificar:
        respuesta = api_client.post(URL, {"id_token": "x"}, format="json")

    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "google_no_configurado"
    verificar.assert_not_called()


def test_si_no_se_puede_consultar_a_google_responde_503(api_client):
    with mock.patch(VERIFICAR, side_effect=google_exceptions.TransportError("sin red")):
        respuesta = api_client.post(URL, {"id_token": "x"}, format="json")

    assert respuesta.status_code == 503


def test_falta_el_id_token(api_client):
    respuesta = api_client.post(URL, {}, format="json")

    assert respuesta.status_code == 400
    assert "id_token" in respuesta.json()["campos"]


def test_es_publico_aunque_llegue_un_token_viejo(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer token-viejo")
    assert login_google(api_client).status_code == 200


def test_solo_acepta_post(api_client):
    assert api_client.get(URL).status_code == 405


# --- Verificación real de la firma (sin internet) ------------------------------------------
# Se firma un ID token con una llave propia y se hace pasar su certificado por el de Google,
# para comprobar que google-auth de verdad revisa firma, audiencia y vencimiento.

@pytest.fixture(scope="module")
def llave_google():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "prueba-google")])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    certificado = (
        x509.CertificateBuilder().subject_name(nombre).issuer_name(nombre)
        .public_key(privada.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(days=1)).not_valid_after(ahora + datetime.timedelta(days=1))
        .sign(privada, hashes.SHA256())
    )
    pem_privada = privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    firmante = crypt.RSASigner.from_string(pem_privada, key_id="llave-prueba")
    return firmante, {"llave-prueba": certificado.public_bytes(serialization.Encoding.PEM)}


def firmar(firmante, **cambios):
    ahora = int(time.time())
    datos = datos_google(iat=ahora, exp=ahora + 3600)
    datos.update(cambios)
    return google_jwt.encode(firmante, datos).decode()


@pytest.mark.parametrize(
    ("cambios", "esperado"),
    [
        ({}, 200),
        ({"aud": "otra-app.apps.googleusercontent.com"}, 401),  # emitido para otra app
        ({"iss": "https://evil.example.com"}, 401),
        ({"exp": int(time.time()) - 3600}, 401),  # vencido
    ],
)
def test_verificacion_real_de_firma_audiencia_y_vencimiento(api_client, llave_google, cambios, esperado):
    firmante, certificados = llave_google
    token = firmar(firmante, **cambios)
    with mock.patch("google.oauth2.id_token._fetch_certs", return_value=certificados):
        respuesta = api_client.post(URL, {"id_token": token}, format="json")

    assert respuesta.status_code == esperado


def test_token_alterado_no_pasa(api_client, llave_google):
    firmante, certificados = llave_google
    encabezado, cuerpo, firma = firmar(firmante).split(".")
    alterado = ".".join([encabezado, cuerpo, firma[:-4] + ("AAAA" if firma[-4:] != "AAAA" else "BBBB")])
    with mock.patch("google.oauth2.id_token._fetch_certs", return_value=certificados):
        respuesta = api_client.post(URL, {"id_token": alterado}, format="json")

    assert respuesta.status_code == 401