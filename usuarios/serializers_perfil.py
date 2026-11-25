"""Serialización del perfil propio (HU-21 / ST-163)."""

from rest_framework import serializers

from usuarios.models import Canal, Usuario


CAMPOS_EDITABLES_PERFIL = ("nombre", "apellidos", "canal_preferido")
MENSAJE_CAMPO_NO_EDITABLE = "Este campo no se puede modificar desde el perfil."


class PerfilSerializer(serializers.ModelSerializer):
    """Muestra el perfil propio y limita la edición a los campos de ST-163.

    El correo y el teléfono son informativos. Su cambio con contraseña y código
    de verificación pertenece a ST-164, por lo que este serializer los mantiene
    como solo lectura y rechaza explícitamente cualquier intento de modificarlos.
    """

    nombre = serializers.CharField(source="first_name", max_length=150, required=False)
    apellidos = serializers.CharField(source="last_name", max_length=150, required=False)
    correo = serializers.EmailField(source="email", read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "nombre",
            "apellidos",
            "correo",
            "telefono",
            "canal_preferido",
            "rol",
            "estado",
        )
        read_only_fields = ("id", "correo", "telefono", "rol", "estado")

    def to_internal_value(self, data):
        no_editables = sorted(set(data) - set(CAMPOS_EDITABLES_PERFIL))
        if no_editables:
            raise serializers.ValidationError(
                {campo: [MENSAJE_CAMPO_NO_EDITABLE] for campo in no_editables}
            )
        return super().to_internal_value(data)

    def validate_canal_preferido(self, valor):
        """WhatsApp solo puede elegirse si la cuenta ya tiene teléfono."""
        if valor == Canal.WHATSAPP and not getattr(self.instance, "telefono", None):
            raise serializers.ValidationError(
                "Registra un teléfono antes de elegir WhatsApp."
            )
        return valor
