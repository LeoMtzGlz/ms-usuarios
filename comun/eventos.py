"""registrar_evento(): punto único para la bitácora de auditoría.

Escribe una línea en el log "svc.auditoria" y guarda el evento en la tabla
EventoAuditoria. Si el guardado falla, se registra el error y el flujo que
llamó sigue sin enterarse.
"""
import ipaddress
import json
import logging

from django.db import transaction

from comun.models import EventoAuditoria

logger = logging.getLogger("svc.auditoria")

CLAVES_SENSIBLES = ("password", "contrasena", "codigo", "token", "refresh", "access", "secreto")


def limpiar_detalles(detalles):
    """Quita cualquier dato sensible antes de registrar, a cualquier profundidad."""
    if isinstance(detalles, dict):
        return {
            k: "***" if any(s in str(k).lower() for s in CLAVES_SENSIBLES) else limpiar_detalles(v)
            for k, v in detalles.items()
        }
    if isinstance(detalles, (list, tuple)):
        return [limpiar_detalles(v) for v in detalles]
    return detalles


def ip_de(request) -> str | None:
    if request is None:
        return None
    ip = request.META.get("REMOTE_ADDR")
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return None
    return ip


def registrar_evento(accion: str, usuario=None, request=None, resultado: str = "ok", **detalles) -> None:
    registro = {
        "accion": accion,
        "resultado": resultado,
        "usuario_id": str(usuario.pk) if usuario is not None and usuario.pk else None,
        "ip": ip_de(request),
        "detalles": limpiar_detalles(detalles),
    }
    logger.info(json.dumps(registro, ensure_ascii=False, default=str))
    try:
        # atomic = savepoint: un error de BD no deja rota la transacción del llamador
        with transaction.atomic():
            EventoAuditoria.objects.create(
                usuario=usuario if usuario is not None and usuario.pk else None,
                accion=accion,
                resultado=resultado,
                ip=registro["ip"],
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request is not None else "",
                detalles=registro["detalles"],
            )
    except Exception:
        logger.exception("No se pudo guardar el evento de auditoría")
