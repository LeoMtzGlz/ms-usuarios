from django.conf import settings
from django.db import models


class CanalNotificacion(models.TextChoices):
    CORREO = "correo", "Correo"
    WHATSAPP = "whatsapp", "WhatsApp"
    CONSOLA = "consola", "Consola"


class Notificacion(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ENVIADA = "enviada"
    ESTADO_FALLIDA = "fallida"
    ESTADOS = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ENVIADA, "Enviada"),
        (ESTADO_FALLIDA, "Fallida"),
    ]

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="destinatario",
    )
    canal = models.CharField(
        "canal", max_length=10, choices=CanalNotificacion.choices
    )
    plantilla = models.CharField("plantilla", max_length=100)
    contexto = models.JSONField(
        "contexto", default=dict, help_text="Datos para renderizar la plantilla."
    )
    estado = models.CharField(
        "estado", max_length=10, choices=ESTADOS, default=ESTADO_PENDIENTE
    )
    intentos = models.PositiveSmallIntegerField("intentos", default=0)
    error = models.TextField("error", blank=True, default="")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        indexes = [
            models.Index(fields=["estado", "creado_en"], name="noti_estado_creado_idx"),
        ]

    def __str__(self):
        return f"{self.destinatario_id} - {self.plantilla} ({self.estado})"