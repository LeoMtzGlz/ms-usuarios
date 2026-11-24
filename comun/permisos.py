"""
T-13 Roles y permisos del microservicio ms-usuarios.
T-13/ST-122 — Crear las clases de permiso en comun/permisos.py
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.settings import api_settings as drf_settings

from comun.roles import Rol


def _claim(request, nombre):
    """Devuelve un claim del token de acceso o None si no hay token o no existe."""
    token = getattr(request, "auth", None)
    if token is None:
        return None
    try:
        return token.get(nombre)
    except AttributeError:
        return None


def rol_del_token(request):
    return _claim(request, "rol")


def id_del_token(request):
    claim = getattr(settings, "SIMPLE_JWT", {}).get("USER_ID_CLAIM", "user_id")
    valor = _claim(request, claim)
    return None if valor is None else str(valor)


def _autenticado(request):
    return bool(request.user and request.user.is_authenticated)


class _RolRequerido(BasePermission):
    roles_permitidos: tuple = ()
    message = "No tienes permiso para esta acción."

    def has_permission(self, request, view):
        return _autenticado(request) and rol_del_token(request) in self.roles_permitidos


class EsAdministrador(_RolRequerido):
    roles_permitidos = (Rol.ADMINISTRADOR,)


class EsOperativo(_RolRequerido):
    roles_permitidos = (Rol.OPERATIVO,)


class EsCliente(_RolRequerido):
    roles_permitidos = (Rol.CLIENTE,)


class EsDuenoOAdmin(BasePermission):
    """El administrador pasa siempre; los demás, solo sobre objetos propios.

    El objeto puede ser un Usuario (se compara su pk) o cualquier modelo con
    `usuario_id`. La revisión por objeto solo corre si la vista usa get_object().
    """

    message = "No tienes permiso sobre este recurso."

    def has_permission(self, request, view):
        return _autenticado(request)

    def has_object_permission(self, request, view, obj):
        if rol_del_token(request) == Rol.ADMINISTRADOR:
            return True
        dueno = obj.pk if isinstance(obj, get_user_model()) else getattr(obj, "usuario_id", None)
        return dueno is not None and str(dueno) == id_del_token(request)


def permisos_por_defecto_mas(*clases):
    """Permisos por defecto de settings + los indicados.

    DRF reemplaza (no suma) la lista cuando una vista o un @action declara
    permission_classes. Úsalo para no perder IsAuthenticated ni, más adelante,
    ContrasenaDefinitiva:  @action(..., permission_classes=permisos_por_defecto_mas(EsAdministrador))
    """
    return [*drf_settings.DEFAULT_PERMISSION_CLASSES, *clases]


# t-12/st-116 (HU-12): bloquear todo mientras la contraseña sea temporal
class ContrasenaDefinitiva(BasePermission):
    """Mientras el token traiga debe_cambiar_password=True, responde 403 debe_cambiar_password.

    Está en DEFAULT_PERMISSION_CLASSES, así que aplica a todos los endpoints. Los que
    deben seguir funcionando con la contraseña temporal (cambiar-password de HU-11)
    declaran su propia lista, p. ej. permission_classes = [IsAuthenticated].
    Las peticiones sin token pasan aquí y las rechaza IsAuthenticated (401).
    El mensaje y el código son los de DebeCambiarPassword (comun/errores.py); no se
    importa esa clase para evitar una importación circular con DRF.
    """

    message = "Debes cambiar tu contraseña temporal antes de continuar."
    code = "debe_cambiar_password"

    def has_permission(self, request, view):
        return _claim(request, "debe_cambiar_password") is not True