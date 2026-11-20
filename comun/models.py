"""Modelos compartidos del servicio.

hu-26/st-187: EventoAuditoria es la tabla de la bitácora. La llena registrar_evento()
(comun/eventos.py, st-188) y la consulta el endpoint GET /api/v1/auditoria/ (st-189).
"""
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class ResultadoEvento(models.TextChoices):
    OK = "ok", "Correcto"
    ERROR = "error", "Error"


class EventoAuditoria(models.Model):
    """Una acción registrada en la bitácora: quién, qué, con qué resultado, desde dónde y cuándo.

    Nunca guarda contraseñas, códigos ni tokens: `detalles` llega ya pasado por limpiar_detalles().
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
        verbose_name="usuario",
        help_text="Vacío en un login fallido o en un evento sin sesión.",
    )
    accion = models.CharField("acción", max_length=50, help_text="Por ejemplo: login, logout, rol_cambiado.")
    resultado = models.CharField(
        "resultado", max_length=10, choices=ResultadoEvento.choices, default=ResultadoEvento.OK
    )
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.TextField("user agent", blank=True, default="")
    # DjangoJSONEncoder: un UUID, una fecha o un Decimal en los detalles se guardan como texto en vez de tronar.
    detalles = models.JSONField("detalles", default=dict, blank=True, encoder=DjangoJSONEncoder)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"
        ordering = ["-fecha"]
        indexes = [
            # Índice por fecha que pide el backlog: orden y filtros por rango de fechas.
            models.Index(fields=["fecha"], name="auditoria_fecha_idx"),
            # Para el filtro por acción y fechas de la st-189.
            models.Index(fields=["accion", "fecha"], name="auditoria_accion_fecha_idx"),
        ]

    def __str__(self):
        cuando = f" {self.fecha:%Y-%m-%d %H:%M}" if self.fecha else ""
        return f"{self.accion} ({self.resultado}){cuando}"
