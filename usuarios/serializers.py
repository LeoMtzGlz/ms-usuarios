"""Serializers de la app usuarios."""
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from comun.roles import Rol
from usuarios.models import Canal, Estado, Usuario
from usuarios.telefono import normalizar_telefono

CORREO_REGISTRADO = "Este correo ya está registrado."
TELEFONO_REGISTRADO = "Este teléfono ya está registrado."


class RegistroSerializer(serializers.Serializer):
    """HU-02 / ST-65: valida los datos del registro de un cliente y crea la cuenta.

    - Las contraseñas son write_only: nunca aparecen en una respuesta.
    - El correo se guarda sin espacios y en minúsculas; el teléfono, en E.164.
    - Correo (sin importar mayúsculas) y teléfono no pueden estar ya registrados.
    - La contraseña debe coincidir con su confirmación y cumplir AUTH_PASSWORD_VALIDATORS (T-12).
    - Sin aceptar el aviso de privacidad no se crea la cuenta; se guardan fecha y versión.
    - La cuenta nace pendiente y con rol cliente, sin importar lo que mande el cliente.
    """

    nombre = serializers.CharField(max_length=150, trim_whitespace=True)
    apellidos = serializers.CharField(max_length=150, trim_whitespace=True)
    correo = serializers.EmailField(max_length=254)
    telefono = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    password_confirmacion = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )
    canal_preferido = serializers.ChoiceField(choices=Canal.choices, default=Canal.CORREO)
    acepto_privacidad = serializers.BooleanField(write_only=True)


    # Validaciones por campo 

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

    def validate_acepto_privacidad(self, valor):
        if not valor:
            raise serializers.ValidationError("Debes aceptar el aviso de privacidad para crear tu cuenta.")
        return valor
    

    # Validaciones entre campos

    def validate(self, datos):
        if datos["password"] != datos["password_confirmacion"]:
            raise serializers.ValidationError({"password_confirmacion": ["Las contraseñas no coinciden."]})

        # Usuario sin guardar, para que UserAttributeSimilarityValidator compare con correo y nombre
        candidato = Usuario(email=datos["correo"], first_name=datos["nombre"], last_name=datos["apellidos"])
        try:
            validate_password(datos["password"], user=candidato)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return datos
    

    # Creación

    def create(self, datos):
        try:
            with transaction.atomic():
                return Usuario.objects.create_user(
                    email=datos["correo"],
                    password=datos["password"],
                    first_name=datos["nombre"],
                    last_name=datos["apellidos"],
                    telefono=datos["telefono"],
                    canal_preferido=datos["canal_preferido"],
                    rol=Rol.CLIENTE,
                    estado=Estado.PENDIENTE,
                    acepto_privacidad_en=timezone.now(),
                    version_privacidad=settings.VERSION_AVISO_PRIVACIDAD,
                )
        except IntegrityError as error:
            # Dos registros simultáneos con el mismo dato: lo frena la restricción única de la base
            if "email" in str(error).lower():
                raise serializers.ValidationError({"correo": [CORREO_REGISTRADO]}) from error
            raise serializers.ValidationError({"telefono": [TELEFONO_REGISTRADO]}) from error

    def to_representation(self, usuario):
        """Respuesta del registro: datos públicos de la cuenta, nunca la contraseña."""
        return {
            "id": str(usuario.id),
            "nombre": usuario.first_name,
            "apellidos": usuario.last_name,
            "correo": usuario.email,
            "telefono": usuario.telefono,
            "canal_preferido": usuario.canal_preferido,
            "rol": usuario.rol,
            "estado": usuario.estado,
        }