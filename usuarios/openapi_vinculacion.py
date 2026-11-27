"""
Esquemas OpenAPI para el contrato genérico de vinculación (HU-38 / ST-238).

Este módulo documenta el contrato; no implementa la integración HTTP.
"""

from rest_framework import serializers

from usuarios.serializers_admin import AltaUsuarioSerializer


class VinculacionRequestSerializer(serializers.Serializer):
    """Datos opcionales para solicitar la vinculación de una entidad externa."""

    tipo_entidad = serializers.CharField(
        help_text=(
            "Tipo genérico de entidad externa. "
            "Ejemplo: chofer; pueden existir otros tipos de entidad."
        ),
    )
    entidad_id = serializers.UUIDField(
        help_text="UUID de la entidad en el servicio externo.",
    )


class AltaUsuarioConVinculacionSchemaSerializer(AltaUsuarioSerializer):
    """Esquema de alta que incluye la vinculación opcional."""

    vinculacion = VinculacionRequestSerializer(
        required=False,
        help_text=(
            "Si se omite, el alta conserva el comportamiento habitual "
            "y no solicita una vinculación externa."
        ),
    )


class EntidadVinculableSerializer(serializers.Serializer):
    """Representación de la entidad enviada al servicio externo."""

    tipo = serializers.CharField()
    id = serializers.UUIDField()


class SolicitudVinculacionExternaSerializer(serializers.Serializer):
    """Payload que el adaptador enviará al servicio externo."""

    user_id = serializers.UUIDField()
    entidad = EntidadVinculableSerializer()


class ErrorVinculacionSerializer(serializers.Serializer):
    """Formato estándar de error de la API."""

    codigo = serializers.CharField()
    mensaje = serializers.CharField()
    campos = serializers.DictField()