"""t-22/st-167 (HU-22): registrar cada intento de login en RegistroAcceso.

- IP: REMOTE_ADDR; X-Forwarded-For solo si la petición viene de un proxy de PROXIES_CONFIABLES.
- Dispositivo: texto legible con la librería user-agents, p. ej. "Chrome 131 en Windows 10".
"""
import ipaddress

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from user_agents import parse

from usuarios.telefono import normalizar_telefono

LARGO_DISPOSITIVO = 120
LARGO_USER_AGENT = 500


def _es_ip(valor):
    try:
        ipaddress.ip_address(valor)
    except ValueError:
        return False
    return True


def ip_del_request(request):
    """IP del cliente. Solo se confía en X-Forwarded-For si la petición viene de un proxy propio.

    X-Forwarded-For lo puede escribir el cliente, así que se lee de derecha a izquierda,
    saltando los proxies de PROXIES_CONFIABLES, y se toma la primera IP que no sea de ellos.
    Cualquier valor que no sea una IP válida se descarta (nunca rompe el login).
    """
    if request is None:
        return None
    remota = request.META.get("REMOTE_ADDR") or None
    remota = remota if remota and _es_ip(remota) else None
    confiables = set(getattr(settings, "PROXIES_CONFIABLES", []))
    if remota is None or remota not in confiables:
        return remota
    reenviada = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
    for ip in reversed(reenviada):
        if not _es_ip(ip):
            break
        if ip not in confiables:
            return ip
    return remota


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