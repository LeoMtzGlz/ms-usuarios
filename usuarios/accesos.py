"""t-22/st-167 (HU-22): registrar cada intento de login en RegistroAcceso.

- IP: el primer valor de X-Forwarded-For (la IP real detrás del proxy) o REMOTE_ADDR.
- Dispositivo: texto legible con la librería user-agents, p. ej. "Chrome 131 en Windows 10".
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from user_agents import parse

from usuarios.telefono import normalizar_telefono

LARGO_DISPOSITIVO = 120
LARGO_USER_AGENT = 500


def ip_del_request(request):
    """IP del cliente: primero X-Forwarded-For, si no, REMOTE_ADDR. None si no hay request."""
    if request is None:
        return None
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if reenviada:
        return reenviada.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def dispositivo_legible(user_agent):
    """Convierte el User-Agent en algo como "Chrome 131 en Windows 10" o "Mobile Safari 17 en iOS 17.1"."""
    if not user_agent:
        return "Desconocido"
    ua = parse(user_agent)
    navegador = " ".join(p for p in (ua.browser.family, ua.browser.version_string.split(".")[0]) if p)
    sistema = " ".join(p for p in (ua.os.family, ua.os.version_string) if p)
    partes = [p for p in (navegador, sistema) if p and p != "Other"]
    if not partes:
        return "Desconocido"
    return " en ".join(partes)[:LARGO_DISPOSITIVO]


def buscar_usuario(identificador):
    """Busca la cuenta por correo o teléfono (como EmailOrPhoneBackend), sin revisar la contraseña."""
    if not identificador:
        return None
    Usuario = get_user_model()
    usuario = Usuario.objects.filter(email__iexact=identificador).first()
    if usuario is None:
        try:
            usuario = Usuario.objects.filter(telefono=normalizar_telefono(identificador)).first()
        except ValidationError:
            usuario = None
    return usuario


def registrar_acceso(request, usuario, exitoso):
    """Guarda un RegistroAcceso. Si la cuenta no existe (usuario None) no se guarda nada."""
    from usuarios.models import RegistroAcceso

    if usuario is None:
        return None
    user_agent = request.META.get("HTTP_USER_AGENT", "") if request is not None else ""
    return RegistroAcceso.objects.create(
        usuario=usuario,
        ip=ip_del_request(request),
        dispositivo=dispositivo_legible(user_agent),
        user_agent=user_agent[:LARGO_USER_AGENT],
        exitoso=exitoso,
    )