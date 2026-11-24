"""Serializers de la app usuarios."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from comun.roles import Rol
from comun.validadores import AYUDA_POLITICA_PASSWORD # t-12/st-105
from usuarios.models import Canal, Estado, Proposito, Usuario
from usuarios.privacidad import datos_aceptacion_privacidad
from usuarios.telefono import normalizar_telefono

CORREO_REGISTRADO = "Este correo ya está registrado."
TELEFONO_REGISTRADO = "Este teléfono ya está registrado."

class RegistroSerializer(serializers.Serializer):
    """HU-02 / ST-65: valida los datos del registro de un cliente y crea la cuenta."""

    nombre = serializers.CharField(max_length=150, trim_whitespace=True)
    apellidos = serializers.CharField(max_length=150, trim_whitespace=True)
    correo = serializers.EmailField(max_length=254)
    telefono = serializers.CharField(max_length=30)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
        help_text=AYUDA_POLITICA_PASSWORD,
    )
    password_confirmacion = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    canal_preferido = serializers.ChoiceField(choices=Canal.choices, default=Canal.CORREO)
    acepto_privacidad = serializers.BooleanField(write_only=True)

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

    def validate(self, datos):
        if datos["password"] != datos["password_confirmacion"]:
            raise serializers.ValidationError({"password_confirmacion": ["Las contraseñas no coinciden."]})
        candidato = Usuario(email=datos["correo"], first_name=datos["nombre"], last_name=datos["apellidos"])
        try:
            validate_password(datos["password"], user=candidato)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return datos

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
                    **datos_aceptacion_privacidad(),
                )
        except IntegrityError as error:
            if "email" in str(error).lower():
                raise serializers.ValidationError({"correo": [CORREO_REGISTRADO]}) from error
            raise serializers.ValidationError({"telefono": [TELEFONO_REGISTRADO]}) from error

    def to_representation(self, usuario):
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

class ActivarSerializer(serializers.Serializer):
    """HU-03 / ST-72: recibe identificador (correo o teléfono) + código."""

    identificador = serializers.CharField(max_length=254, trim_whitespace=True)
    codigo = serializers.CharField(max_length=6, min_length=6, trim_whitespace=True)

    def validate(self, datos):
        identificador = datos["identificador"].strip()
        codigo = datos["codigo"].strip()
        usuario = Usuario.objects.filter(email__iexact=identificador).first()
        if usuario is None:
            try:
                telefono = normalizar_telefono(identificador)
                usuario = Usuario.objects.filter(telefono=telefono).first()
            except DjangoValidationError:
                usuario = None

        if usuario is None:
            raise serializers.ValidationError({"identificador": ["No existe una cuenta con ese correo o teléfono."]})

        datos["usuario"] = usuario

        from usuarios.codigos import verificar_codigo

        try:
            registro = verificar_codigo(usuario, Proposito.ACTIVACION, codigo)
        except ValueError as error:
            codigo_error = str(error)
            if codigo_error == "codigo_expirado":
                raise serializers.ValidationError({"codigo": ["El código ya venció. Pide uno nuevo."]})
            if codigo_error == "codigo_bloqueado":
                raise serializers.ValidationError({"codigo": ["Demasiados intentos. Pide un código nuevo."]})
            raise serializers.ValidationError({"codigo": ["Código incorrecto."]})

        datos["registro_codigo"] = registro   
        return datos                          
    
class CodigoDosFactoresSerializer(serializers.Serializer):
    """T-30 / ST-206: código de 6 dígitos de la app autenticadora."""

    codigo = serializers.RegexField(
        r"^\d{6}$",
        error_messages={"invalid": "El código debe tener 6 dígitos."},
    )


class CambiarPasswordSerializer(serializers.Serializer):
    """HU-11 / ST-112: cambio de contraseña con sesión iniciada.

    - Requiere la contraseña actual (se verifica con check_password).
    - La nueva debe cumplir AUTH_PASSWORD_VALIDATORS y coincidir con la confirmación.
    - No emite tokens: eso corresponde a ST-113.
    """

    password_actual = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password_nueva = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
        help_text=AYUDA_POLITICA_PASSWORD,
    )
    password_confirmacion = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_password_actual(self, valor):
        usuario = self.context["request"].user
        if not usuario.check_password(valor):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return valor

    def validate(self, datos):
        if datos["password_nueva"] != datos["password_confirmacion"]:
            raise serializers.ValidationError(
                {"password_confirmacion": ["Las contraseñas no coinciden."]}
            )
        if datos["password_nueva"] == datos["password_actual"]:
            raise serializers.ValidationError(
                {"password_nueva": ["La nueva contraseña debe ser distinta a la actual."]}
            )
        usuario = self.context["request"].user
        try:
            validate_password(datos["password_nueva"], user=usuario)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password_nueva": list(error.messages)}
            ) from error
        return datos

    def save(self, **kwargs):
        """Aplica el cambio usando el método del modelo (único lugar que muta la contraseña)."""
        usuario = self.context["request"].user
        request = self.context.get("request")
        usuario.cambiar_password(self.validated_data["password_nueva"], request=request)
        return usuario
