"""Pruebas de t-22/st-167 (HU-22): cada login guarda fecha, IP, dispositivo y si fue exitoso."""
import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from comun.errores import CredencialesInvalidas, CuentaInactiva, CuentaPendiente
from usuarios.accesos import buscar_usuario, dispositivo_legible, ip_del_request
from usuarios.models import Estado, RegistroAcceso, Usuario
from usuarios.tokens import CustomTokenObtainPairSerializer

pytestmark = pytest.mark.django_db

CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
)


def _request(**meta):
    request = APIRequestFactory().post("/api/v1/auth/login/", **meta)
    request.user = AnonymousUser()
    return request


def _login(identificador, password, request):
    serializer = CustomTokenObtainPairSerializer(
        data={"email": identificador, "password": password}, context={"request": request}
    )
    return serializer.is_valid(raise_exception=True)


@pytest.fixture
def activo():
    return Usuario.objects.create_user(email="activo@ejemplo.com", password="Password123", estado=Estado.ACTIVO)


def test_login_exitoso_guarda_fecha_ip_dispositivo(activo, llaves):
    _login("activo@ejemplo.com", "Password123", _request(REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT=CHROME_WINDOWS))

    acceso = RegistroAcceso.objects.get(usuario=activo)
    assert acceso.exitoso is True
    assert acceso.ip == "10.0.0.5"
    assert acceso.dispositivo == "Chrome 131 en Windows 10"
    assert acceso.user_agent == CHROME_WINDOWS
    assert acceso.fecha is not None


def test_contrasena_incorrecta_guarda_acceso_fallido(activo):
    with pytest.raises(CredencialesInvalidas):
        _login("activo@ejemplo.com", "Equivocada1", _request(HTTP_USER_AGENT=SAFARI_IPHONE))

    acceso = RegistroAcceso.objects.get(usuario=activo)
    assert acceso.exitoso is False
    assert acceso.dispositivo == "Mobile Safari 17 en iOS 17.1"


def test_correo_que_no_existe_no_guarda_nada():
    with pytest.raises(CredencialesInvalidas):
        _login("nadie@ejemplo.com", "Password123", _request())

    assert RegistroAcceso.objects.count() == 0


@pytest.mark.parametrize(("estado", "error"), [(Estado.PENDIENTE, CuentaPendiente), (Estado.INACTIVO, CuentaInactiva)])
def test_cuenta_pendiente_o_inactiva_guarda_acceso_fallido(estado, error):
    usuario = Usuario.objects.create_user(email="otra@ejemplo.com", password="Password123", estado=estado)

    with pytest.raises(error):
        _login("otra@ejemplo.com", "Password123", _request())

    assert RegistroAcceso.objects.get(usuario=usuario).exitoso is False


def test_ip_toma_el_primer_valor_de_x_forwarded_for():
    request = _request(HTTP_X_FORWARDED_FOR="200.1.2.3, 10.0.0.1", REMOTE_ADDR="10.0.0.1")

    assert ip_del_request(request) == "200.1.2.3"


def test_ip_sin_proxy_usa_remote_addr():
    assert ip_del_request(_request(REMOTE_ADDR="192.168.1.20")) == "192.168.1.20"


def test_dispositivo_desconocido():
    assert dispositivo_legible("") == "Desconocido"
    assert dispositivo_legible("algo-raro") == "Desconocido"


def test_buscar_usuario_ignora_mayusculas(activo):
    assert buscar_usuario("ACTIVO@Ejemplo.com") == activo
    assert buscar_usuario("") is None


def test_registros_ordenados_del_mas_reciente(activo, llaves):
    request = _request(REMOTE_ADDR="10.0.0.5")
    with pytest.raises(CredencialesInvalidas):
        _login("activo@ejemplo.com", "Equivocada1", request)
    _login("activo@ejemplo.com", "Password123", request)

    assert [a.exitoso for a in activo.accesos.all()] == [True, False]