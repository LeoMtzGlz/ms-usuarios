from rest_framework import serializers


class ActivarSerializer(serializers.Serializer):
    identificador = serializers.CharField(max_length=254)
    codigo = serializers.RegexField(
        r"^\d{6}$", error_messages={"invalid": "El código debe tener 6 dígitos."}
    )