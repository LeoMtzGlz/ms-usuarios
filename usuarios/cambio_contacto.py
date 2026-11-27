"""Cambio verificado del correo o teléfono propio (HU-21 / ST-164)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from comun.eventos import registrar_evento
from usuarios.codigos import generar_codigo_contacto, verificar_codigo
from usuarios.models import Proposito, Usuario
from usuarios.telefono import normalizar_telefono


TIPO_CORREO = "correo"
TIPO_TELEFONO = "telefono"
TIPOS_CONTACTO = (TIPO_CORREO, TIPO_TELEFONO)
MENSAJE_DUPLICADO = "Este dato ya está registrado en otra cuenta."


def normalizar_contacto(tipo: str, valor: str) -> str:
    """Valida y normaliza el contacto antes de compararlo o guardarlo."""
    if tipo == TIPO_CORREO:
        try:
            correo = serializers.EmailField().run_validation(valor)
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"valor": list(error.detail)}) from error
        return correo.strip().lower()
    try:
        return normalizar_telefono(valor)
    except DjangoValidationError as error:
        raise serializers.ValidationError({"valor": list(error.messages)}) from error


def validar_contacto_disponible(usuario: Usuario, tipo: str, valor: str) -> None:
    """Rechaza el dato actual y los contactos que pertenecen a otra cuenta."""
    if tipo == TIPO_CORREO:
        actual = usuario.email.lower()
        ocupada = Usuario.objects.filter(email__iexact=valor).exclude(pk=usuario.pk).exists()
    else:
        actual = usuario.telefono
        ocupada = Usuario.objects.filter(telefono=valor).exclude(pk=usuario.pk).exists()

    if actual == valor:
        raise serializers.ValidationError({"valor": ["Tu cuenta ya usa este dato."]})
    if ocupada:
        raise serializers.ValidationError({"valor": [MENSAJE_DUPLICADO]})


class ContactoBaseSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TIPOS_CONTACTO)
    valor = serializers.CharField(max_length=254, trim_whitespace=True)

    def validate(self, datos):
        usuario = self.context["request"].user
        valor = normalizar_contacto(datos["tipo"], datos["valor"])
        validar_contacto_disponible(usuario, datos["tipo"], valor)
        datos["valor"] = valor
        return datos


class SolicitarCambioContactoSerializer(ContactoBaseSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, datos):
        datos = super().validate(datos)
        if not self.context["request"].user.check_password(datos["password"]):
            raise serializers.ValidationError({"password": ["La contraseña es incorrecta."]})
        return datos

    def save(self, **kwargs):
        usuario = self.context["request"].user
        registro = generar_codigo_contacto(
            usuario,
            self.validated_data["tipo"],
            self.validated_data["valor"],
        )
        registrar_evento(
            "cambio_contacto_solicitado",
            usuario,
            self.context["request"],
            tipo=self.validated_data["tipo"],
        )
        return registro


class ConfirmarCambioContactoSerializer(ContactoBaseSerializer):
    codigo = serializers.RegexField(
        r"^\d{6}$",
        error_messages={"invalid": "El código debe tener 6 dígitos."},
    )

    def _traducir_error_codigo(self, error: ValueError):
        mensajes = {
            "codigo_expirado": "El código ya venció. Solicita uno nuevo.",
            "codigo_bloqueado": "Demasiados intentos. Solicita un código nuevo.",
            "codigo_invalido": "El código es incorrecto.",
        }
        raise serializers.ValidationError(
            {"codigo": [mensajes.get(str(error), mensajes["codigo_invalido"])]}
        ) from error

    def save(self, **kwargs):
        request = self.context["request"]
        tipo = self.validated_data["tipo"]
        valor = self.validated_data["valor"]
        codigo = self.validated_data["codigo"]

        error_codigo = None
        try:
            with transaction.atomic():
                usuario = Usuario.objects.select_for_update().get(pk=request.user.pk)
                validar_contacto_disponible(usuario, tipo, valor)
                try:
                    verificar_codigo(
                        usuario,
                        Proposito.CAMBIO_CONTACTO,
                        codigo,
                        vinculacion=f"{tipo}:{valor}",
                    )
                except ValueError as error:
                    error_codigo = error

                if error_codigo is None:
                    if tipo == TIPO_CORREO:
                        usuario.email = valor
                        usuario.email_verificado = True
                        campos = ["email", "email_verificado"]
                    else:
                        usuario.telefono = valor
                        usuario.telefono_verificado = True
                        campos = ["telefono", "telefono_verificado"]
                    usuario.save(update_fields=campos)
        except IntegrityError as error:
            raise serializers.ValidationError({"valor": [MENSAJE_DUPLICADO]}) from error

        if error_codigo is not None:
            self._traducir_error_codigo(error_codigo)

        registrar_evento(
            "contacto_cambiado",
            usuario,
            request,
            tipo=tipo,
        )
        return usuario


class SolicitarCambioContactoView(GenericAPIView):
    serializer_class = SolicitarCambioContactoSerializer

    @extend_schema(
        summary="Solicitar el cambio de correo o teléfono",
        responses={
            200: OpenApiResponse(description="Código enviado al contacto nuevo"),
            400: OpenApiResponse(description="Contraseña, contacto o formato inválido"),
            401: OpenApiResponse(description="Sin token o token inválido"),
            403: OpenApiResponse(description="La contraseña temporal todavía no se ha cambiado"),
        },
        tags=["perfil"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"mensaje": "Enviamos un código al contacto nuevo."},
            status=status.HTTP_200_OK,
        )


class ConfirmarCambioContactoView(GenericAPIView):
    serializer_class = ConfirmarCambioContactoSerializer

    @extend_schema(
        summary="Confirmar el cambio de correo o teléfono",
        responses={
            200: OpenApiResponse(description="Contacto actualizado"),
            400: OpenApiResponse(description="Código o contacto inválido"),
            401: OpenApiResponse(description="Sin token o token inválido"),
            403: OpenApiResponse(description="La contraseña temporal todavía no se ha cambiado"),
        },
        tags=["perfil"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "mensaje": "Contacto actualizado correctamente.",
                "tipo": serializer.validated_data["tipo"],
            },
            status=status.HTTP_200_OK,
        )
