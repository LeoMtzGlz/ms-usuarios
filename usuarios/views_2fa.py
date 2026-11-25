#t-30/st-206
"""HU-30 / ST-206: activar y confirmar la verificación en dos pasos (2FA)."""
import time

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.errores import CodigoInvalido, DosFactoresNoIniciado, DosFactoresYaActivo
from comun.eventos import registrar_evento
from usuarios.dos_factores import qr_base64, generar_codigos_respaldo
from usuarios.models import Dispositivo2FA
from usuarios.serializers import CodigoDosFactoresSerializer

PASO_TOTP = 30  # segundos que dura cada código


class Activar2FAView(APIView):
    """POST /api/v1/auth/2fa/activar/

    Crea un secreto nuevo (guardado cifrado) y devuelve el QR y el secreto.
    El 2FA NO queda activo hasta confirmar un primer código. Si se vuelve a
    llamar antes de confirmar, se genera un secreto nuevo y el anterior deja de servir.
    """

    @extend_schema(request=None, tags=["auth"])
    def post(self, request):
        with transaction.atomic():
            dispositivo = (
                Dispositivo2FA.objects.select_for_update().filter(usuario=request.user).first()
                or Dispositivo2FA(usuario=request.user)
            )
            if dispositivo.confirmado:
                raise DosFactoresYaActivo()
            secreto = dispositivo.generar_secreto()
            dispositivo.save()

        uri = dispositivo.uri_aprovisionamiento()
        registrar_evento("2fa_activacion_iniciada", request.user, request)
        # El secreto solo se devuelve aquí; nunca va a la bitácora ni a los logs.
        return Response({"secreto": secreto, "uri": uri, "qr_base64": qr_base64(uri)})


class Confirmar2FAView(APIView):
    """POST /api/v1/auth/2fa/confirmar/  {"codigo": "123456"}

    Activa el 2FA solo si el primer código de la app es correcto.
    """

    @extend_schema(request=CodigoDosFactoresSerializer, tags=["auth"])
    def post(self, request):
        serializer = CodigoDosFactoresSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codigo = serializer.validated_data["codigo"]

        with transaction.atomic():
            dispositivo = Dispositivo2FA.objects.select_for_update().filter(usuario=request.user).first()
            if dispositivo is None:
                raise DosFactoresNoIniciado()
            if dispositivo.confirmado:
                raise DosFactoresYaActivo()

            valido = dispositivo.verificar(codigo)
            if valido:
                dispositivo.confirmado = True
                dispositivo.confirmado_en = timezone.now()
                dispositivo.ultimo_intervalo = int(time.time() // PASO_TOTP)  # el código usado no se reutiliza (HU-31)
                dispositivo.save(update_fields=["confirmado", "confirmado_en", "ultimo_intervalo"])
                #? ST-207 (códigos de respaldo): aquí se generarán y se agregarán a la respuesta, una sola vez.
                codigos = generar_codigos_respaldo(request.user) 

        # El evento va fuera de la transacción para que no se pierda si algo se revierte.
        if not valido:
            registrar_evento("2fa_confirmacion_fallida", request.user, request)
            raise CodigoInvalido()

        registrar_evento("2fa_activado", request.user, request)
    
        return Response({
                    "confirmado": True, 
                    "mensaje": "Verificación en dos pasos activada.", 
                    "codigos_respaldo": codigos
                })