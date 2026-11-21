"""Serializers de administración de usuarios (HU-15 en adelante)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from comun.roles import Rol
from usuarios.models import Estado, Usuario
from usuarios.serializers import CORREO_REGISTRADO, TELEFONO_REGISTRADO
from usuarios.telefono import normalizar_telefono


class AltaUsuarioSerializer(serializers.Serializer):
    """HU-15 / ST-140: un administrador da de alta a un usuario operativo.

    - Solo se leen nombre, apellidos, correo y teléfono. Cualquier otro dato que mande el
      cliente (rol, estado, password...) se ignora: la cuenta nace siempre activa, con
      rol operativo y debe_cambiar_password=True.
    - El correo (sin importar mayúsculas) y el teléfono no pueden estar ya registrados.
    - La contraseña temporal no se genera aquí: la vista la crea y la pasa a `save()`.
      Este serializer solo guarda su hash y nunca la devuelve.
    """

    nombre = serializers.CharField(max_length=150, trim_whitespace=True)
    apellidos = serializers.CharField(max_length=150, trim_whitespace=True)
    correo = serializers.EmailField(max_length=254)
    telefono = serializers.CharField(max_length=30)

    def validate_correo(self, valor):
        correo = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=correo).exists():
            raise serializers.ValidationError(CORREO_REGISTRADO)
        return correo

    def validate_telefono(self, valor):
        try:
            telefono = normalizar_telefono(valor)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        if Usuario.objects.filter(telefono=telefono).exists():
            raise serializers.ValidationError(TELEFONO_REGISTRADO)
        return telefono

    def create(self, datos):
        """`datos` trae los campos validados más `contrasena`, que agrega la vista."""
        try:
            with transaction.atomic():
                return Usuario.objects.create_user(
                    email=datos["correo"],
                    password=datos["contrasena"],  # create_user guarda el hash (Argon2)
                    first_name=datos["nombre"],
                    last_name=datos["apellidos"],
                    telefono=datos["telefono"],
                    rol=Rol.OPERATIVO,
                    estado=Estado.ACTIVO,
                    debe_cambiar_password=True,
                )
        except IntegrityError as error:
            # Dos altas simultáneas con el mismo dato: lo frena la restricción única de la base
            if "email" in str(error).lower():
                raise serializers.ValidationError({"correo": [CORREO_REGISTRADO]}) from error
            raise serializers.ValidationError({"telefono": [TELEFONO_REGISTRADO]}) from error

    def to_representation(self, usuario):
        """Datos públicos de la cuenta. La contraseña temporal la agrega la vista."""
        return {
            "id": str(usuario.id),
            "nombre": usuario.first_name,
            "apellidos": usuario.last_name,
            "correo": usuario.email,
            "telefono": usuario.telefono,
            "rol": usuario.rol,
            "estado": usuario.estado,
            "debe_cambiar_password": usuario.debe_cambiar_password,
        }


class UsuarioListaSerializer(serializers.ModelSerializer):
    """HU-16 / ST-145: una fila del listado de usuarios. Solo lectura.

    `bloqueada` no es un campo del modelo: la agrega `usuarios.bloqueos.con_bloqueada()` al
    queryset. Si se usa este serializer con otro queryset hay que anotarlo también.
    Nunca expone la contraseña, token_version ni datos de 2FA.
    """

    nombre = serializers.CharField(source="first_name")
    apellidos = serializers.CharField(source="last_name")
    correo = serializers.EmailField(source="email")
    bloqueada = serializers.BooleanField()
    ultimo_acceso = serializers.DateTimeField(source="last_login", allow_null=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "nombre", "apellidos", "correo", "telefono",
            "rol", "estado", "bloqueada", "ultimo_acceso",
        ]
        read_only_fields = fields
