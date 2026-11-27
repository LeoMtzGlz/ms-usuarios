"""t-32/st-215 (HU-32): desactivar la verificación en dos pasos (2FA).

POST /api/v1/auth/2fa/desactivar/  {"password": "...", "codigo": "123456"}

- Pide la contraseña actual y un código vigente de la app autenticadora.
- Un administrador no puede desactivarla (HU-32): responde 403 admin_requiere_2fa.
- Borra el secreto y los códigos de respaldo, y avisa por correo.
"""
import time

import pyotp
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.errores import AdminRequiere2FA, CodigoInvalido, DosFactoresNoActivo
from comun.eventos import registrar_evento
from comun.roles import Rol
from notificaciones.models import CanalNotificacion
from notificaciones.services import notificar
from usuarios.models import CodigoRespaldo, Dispositivo2FA

PASO_TOTP = 30  # segundos que dura cada código (igual que en views_2fa)
PLANTILLA_AVISO = "2fa_desactivado"
ASUNTO_AVISO = "Se desactivó la verificación en dos pasos"


class Desactivar2FASerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    codigo = serializers.RegexField(
        r"^\d{6}$",
        error_messages={"invalid": "El código debe tener 6 dígitos."},
    )


def intervalo_del_codigo(secreto, codigo, ahora=None):
    """Intervalo TOTP (cada 30 s) al que pertenece el código, o None si no es válido.

    Acepta el intervalo actual, el anterior y el siguiente (como valid_window=1).
    """
    ahora = time.time() if ahora is None else ahora
    totp = pyotp.TOTP(secreto)
    actual = int(ahora // PASO_TOTP)
    for intervalo in (actual, actual - 1, actual + 1):
        if totp.at(intervalo * PASO_TOTP) == codigo:
            return intervalo
    return None


class Desactivar2FAView(APIView):
    """POST /api/v1/auth/2fa/desactivar/ (cliente u operativo dueño de la cuenta)."""

    @extend_schema(
        request=Desactivar2FASerializer,
        responses={
            200: OpenApiResponse(description="2FA desactivado; se envía aviso por correo"),
            400: OpenApiResponse(description="Contraseña o código incorrectos, o 2FA no activo"),
            401: OpenApiResponse(description="No autenticado"),
            403: OpenApiResponse(description="admin_requiere_2fa: un administrador no puede desactivarlo"),
        },
        tags=["auth"],
        summary="Desactivar la verificación en dos pasos",
    )
    def post(self, request):
        usuario = request.user
        if usuario.rol == Rol.ADMINISTRADOR:
            registrar_evento("2fa_desactivacion_rechazada", usuario, request, resultado="rechazado")
            raise AdminRequiere2FA()

        serializer = Desactivar2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        codigo = serializer.validated_data["codigo"]

        if not usuario.check_password(password):
            registrar_evento("2fa_desactivacion_fallida", usuario, request, resultado="fallido", motivo="password")
            raise serializers.ValidationError(
                {"password": ["La contraseña es incorrecta."]}, code="password_incorrecta"
            )

        with transaction.atomic():
            dispositivo = (
                Dispositivo2FA.objects.select_for_update()
                .filter(usuario=usuario, confirmado=True)
                .first()
            )
            if dispositivo is None:
                raise DosFactoresNoActivo()

            intervalo = intervalo_del_codigo(dispositivo.secreto, codigo)
            # Un código que ya se usó (mismo intervalo o anterior) no sirve otra vez.
            reutilizado = (
                intervalo is not None
                and dispositivo.ultimo_intervalo is not None
                and intervalo <= dispositivo.ultimo_intervalo
            )
            valido = intervalo is not None and not reutilizado
            if valido:
                CodigoRespaldo.objects.filter(usuario=usuario).delete()
                dispositivo.delete()
                notificar(
                    usuario,
                    plantilla=PLANTILLA_AVISO,
                    contexto={
                        "asunto": ASUNTO_AVISO,
                        "nombre": usuario.first_name,
                        "fecha": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
                    },
                    canal=CanalNotificacion.CORREO,
                )

        if not valido:
            registrar_evento("2fa_desactivacion_fallida", usuario, request, resultado="fallido", motivo="codigo")
            raise CodigoInvalido()

        registrar_evento("2fa_desactivado", usuario, request)
        return Response({"desactivado": True, "mensaje": "Verificación en dos pasos desactivada."})