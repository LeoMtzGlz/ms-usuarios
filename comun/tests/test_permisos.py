"""
T-13/ST-125 — Pruebas de permisos: cada clase permite y niega a los roles correctos.
Cubre T-13 criterio 2 y HU-13 criterios 1 y 2 (pruebas de ST-122).

El token se simula con un dict para no depender de las llaves RS256 (T-04).
"""

from types import SimpleNamespace

import pytest
from rest_framework.authentication import BaseAuthentication
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from comun.permisos import (
    EsAdministrador,
    EsCliente,
    EsDuenoOAdmin,
    EsOperativo,
    id_del_token,
    rol_del_token,
)
from comun.roles import Rol
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db
fabrica = APIRequestFactory()
DEL_USUARIO = object()


def _token(usuario, rol=DEL_USUARIO):
    token = {"user_id": str(usuario.pk)}
    if rol is DEL_USUARIO:
        token["rol"] = usuario.rol
    elif rol is not None:
        token["rol"] = rol
    return token


class _AutenticacionBearer(BaseAuthentication):
    """Imita a JWTAuthentication: sin token no autentica y pide 'Bearer'.

    Mientras T-04 no configure JWTAuthentication como primera clase de
    DEFAULT_AUTHENTICATION_CLASSES, DRF usa SessionAuthentication y una
    petición sin token responde 403 en lugar de 401.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return 'Bearer realm="api"'


def _llamar(permiso, usuario=None, rol=DEL_USUARIO):
    class Vista(APIView):
        authentication_classes = [_AutenticacionBearer]
        permission_classes = [permiso]

        def get(self, request):
            return Response({"ok": True})

    request = fabrica.get("/prueba/")
    if usuario is not None:
        force_authenticate(request, user=usuario, token=_token(usuario, rol))
    return Vista.as_view()(request)


def _peticion(usuario, rol=DEL_USUARIO):
    return SimpleNamespace(user=usuario, auth=_token(usuario, rol))


MATRIZ = [
    (EsAdministrador, Rol.ADMINISTRADOR, 200),
    (EsAdministrador, Rol.CLIENTE, 403),
    (EsAdministrador, Rol.OPERATIVO, 403),
    (EsOperativo, Rol.OPERATIVO, 200),
    (EsOperativo, Rol.CLIENTE, 403),
    (EsOperativo, Rol.ADMINISTRADOR, 403),
    (EsCliente, Rol.CLIENTE, 200),
    (EsCliente, Rol.OPERATIVO, 403),
    (EsCliente, Rol.ADMINISTRADOR, 403),
]


@pytest.mark.parametrize("permiso,rol,esperado", MATRIZ)
def test_cada_clase_permite_y_niega_por_rol(permiso, rol, esperado):
    """T-13 criterio 2 / HU-13 criterio 1: rol equivocado responde 403."""
    usuario = UsuarioFactory(rol=rol)
    respuesta = _llamar(permiso, usuario)
    assert respuesta.status_code == esperado
    if esperado == 403:
        assert respuesta.data["codigo"] == "sin_permiso"


@pytest.mark.parametrize("permiso", [EsAdministrador, EsOperativo, EsCliente, EsDuenoOAdmin])
def test_sin_token_responde_401(permiso):
    """HU-13 criterio 1: sin token responde 401."""
    respuesta = _llamar(permiso)
    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


def test_token_sin_claim_rol_se_niega():
    usuario = UsuarioFactory(rol=Rol.ADMINISTRADOR)
    assert _llamar(EsAdministrador, usuario, rol=None).status_code == 403


def test_el_rol_se_toma_del_token_y_no_de_la_bd():
    """Decisión de diseño (E06): el rol viaja en el token."""
    usuario = UsuarioFactory(rol=Rol.CLIENTE)
    assert _llamar(EsAdministrador, usuario, rol=Rol.ADMINISTRADOR).status_code == 200


def test_dueno_accede_a_su_propio_usuario():
    cliente = UsuarioFactory(rol=Rol.CLIENTE)
    assert EsDuenoOAdmin().has_object_permission(_peticion(cliente), None, cliente)


def test_cliente_no_accede_a_otro_cliente():
    """HU-13 criterio 2: un cliente no puede ver datos de otro cliente."""
    cliente, otro = UsuarioFactory(rol=Rol.CLIENTE), UsuarioFactory(rol=Rol.CLIENTE)
    assert not EsDuenoOAdmin().has_object_permission(_peticion(cliente), None, otro)


def test_admin_accede_a_cualquier_objeto():
    admin, otro = UsuarioFactory(rol=Rol.ADMINISTRADOR), UsuarioFactory(rol=Rol.CLIENTE)
    assert EsDuenoOAdmin().has_object_permission(_peticion(admin), None, otro)


def test_dueno_por_campo_usuario_id():
    cliente = UsuarioFactory(rol=Rol.CLIENTE)
    recurso = SimpleNamespace(usuario_id=cliente.pk)
    assert EsDuenoOAdmin().has_object_permission(_peticion(cliente), None, recurso)


def test_objeto_sin_dueno_se_niega_a_no_admin():
    cliente = UsuarioFactory(rol=Rol.CLIENTE)
    assert not EsDuenoOAdmin().has_object_permission(_peticion(cliente), None, SimpleNamespace())


def test_lectura_de_claims_sin_token():
    sin_token = SimpleNamespace(user=None, auth=None)
    assert rol_del_token(sin_token) is None
    assert id_del_token(sin_token) is None
