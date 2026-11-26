from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.contrib.auth.password_validation import validate_password

from usuarios.models import Usuario, Proposito
from usuarios.codigos import verificar_codigo
from usuarios.telefono import normalizar_telefono

from django.utils import timezone
from notificaciones.services import notificar


class RestablecerSerializer(serializers.Serializer):
    identificador = serializers.CharField(max_length=254, trim_whitespace=True)
    codigo = serializers.CharField(max_length=6, min_length=6, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmacion = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, data):
        identificador = data["identificador"].strip()
        codigo = data["codigo"].strip()

        # 1. Buscar usuario
        usuario = Usuario.objects.filter(email__iexact=identificador).first()
        if usuario is None:
            try:
                telefono = normalizar_telefono(identificador)
                usuario = Usuario.objects.filter(telefono=telefono).first()
            except DjangoValidationError:
                usuario = None

        if usuario is None:
            raise serializers.ValidationError({"identificador": ["No existe una cuenta con ese correo o teléfono."]})

        # 2. Validar código
        try:
            registro = verificar_codigo(usuario, Proposito.RECUPERACION, codigo)
        except ValueError as error:
            codigo_error = str(error)
            if codigo_error == "codigo_expirado":
                raise serializers.ValidationError({"codigo": ["El código ya venció. Pide uno nuevo."]})
            if codigo_error == "codigo_bloqueado":
                raise serializers.ValidationError({"codigo": ["Demasiados intentos. Pide un código nuevo."]})
            raise serializers.ValidationError({"codigo": ["Código incorrecto."]})

        # 3. Validar contraseñas
        if data["password"] != data["password_confirmacion"]:
            raise serializers.ValidationError({"password_confirmacion": ["Las contraseñas no coinciden."]})

        try:
            validate_password(data["password"], user=usuario)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        # Guardamos los objetos para usarlos en la vista
        data["usuario"] = usuario
        data["registro_codigo"] = registro
        return data


class RestablecerPasswordView(APIView):
    """HU-10 / ST-108: POST /api/v1/auth/restablecer/"""
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["auth"])
    def post(self, request):
        serializer = RestablecerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data["usuario"]
        nueva_password = serializer.validated_data["password"]

        # Cambiar contraseña (esto ya incrementa token_version internamente en el modelo)
        usuario.cambiar_password(nueva_password, request=request)

        # ST-109: Encolar aviso de contraseña cambiada
        notificar(
            usuario=usuario,
            plantilla="password_cambiada",
            contexto={
                "nombre": usuario.first_name or "Usuario",
                "fecha": timezone.now().strftime("%Y-%m-%d %H:%M"),
            },
            canal="correo"
        )

        return Response(
            {"mensaje": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK
        )