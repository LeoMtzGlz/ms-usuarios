"""registrar_evento(): punto único para la bitácora de auditoría.

Versión inicial (T-03): escribe una línea en el log "svc.auditoria".
HU-26 cambiará el cuerpo para guardar también en la tabla EventoAuditoria,
sin tocar a quienes la llaman.
"""
import json
import logging

logger = logging.getLogger("svc.auditoria")

CLAVES_SENSIBLES = ("password", "contrasena", "codigo", "token", "refresh", "access", "secreto")


def limpiar_detalles(detalles: dict) -> dict:
    """Quita cualquier dato sensible antes de registrar."""
    return {
        k: "***" if any(s in k.lower() for s in CLAVES_SENSIBLES) else v for k, v in detalles.items()
    }


def ip_de(request) -> str | None:
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR")


def registrar_evento(accion: str, usuario=None, request=None, resultado: str = "ok", **detalles) -> None:
    registro = {
        "accion": accion,
        "resultado": resultado,
        "usuario_id": str(usuario.pk) if usuario is not None and usuario.pk else None,
        "ip": ip_de(request),
        "detalles": limpiar_detalles(detalles),
    }
    logger.info(json.dumps(registro, ensure_ascii=False, default=str))
