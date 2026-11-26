"""Serializador de la bitácora (HU-26 / ST-189)."""
from rest_framework import serializers

from comun.models import EventoAuditoria


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = EventoAuditoria
        fields = ["id", "usuario", "accion", "resultado", "ip", "user_agent", "detalles", "fecha"]
        read_only_fields = fields
