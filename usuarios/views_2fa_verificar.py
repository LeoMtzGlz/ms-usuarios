"""t-31/st-211: POST /api/v1/auth/2fa/verificar/ (HU-31, criterios 2 y 3).

Segundo paso del login con 2FA. Recibe el token temporal de la st-210 y un código:
- el de 6 dígitos de la app autenticadora, o
- uno de los códigos de respaldo (st-207), que se consume al usarlo. Un código de respaldo
  puede ser solo de números (el alfabeto incluye 2-9): si un código de 6 dígitos no es el de la app,
  se prueba como código de respaldo.

Si el código es correcto se completa el inicio de sesión: se registra el acceso,
se actualiza last_login y se entregan los JWT con emitir_jwt() de tokens.py, los mismos del login
y con la duración de "recordarme" (st-85).

- El mismo código de la app no sirve dos veces: se guarda el último intervalo usado
  en Dispositivo2FA.ultimo_intervalo y solo se aceptan intervalos posteriores.
- Máximo 5 intentos: después del quinto código incorrecto se responde
  429 demasiados_intentos con Retry-After durante 5 minutos, aunque el código sea correcto.
- El token temporal es de un solo uso: después de un inicio de sesión correcto ya no sirve.
"""

import hashlib
import hmac
import time

import pyotp
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.errores import CodigoInvalido, TokenInvalido
from comun.eventos import registrar_evento
from usuarios.accesos import registrar_acceso
from usuarios.dos_factores import usar_codigo_respaldo
from usuarios.login_2fa import VIGENCIA_SEGUNDOS, leer_token_temporal
from usuarios.models import Dispositivo2FA
from usuarios.tokens import emitir_jwt

PASO_TOTP = 30  # segundos que dura cada código de la app (igual que st-206)
MAXIMO_INTENTOS = 5  # HU-31, criterio 3


class VerificarDosFactoresSerializer(serializers.Serializer):
    token_temporal = serializers.CharField()
    codigo = serializers.CharField(max_length=20)


class UsuarioVerificadoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nombre = serializers.CharField()
    email = serializers.EmailField()
    rol = serializers.CharField()


class VerificarDosFactoresRespuestaSerializer(serializers.Serializer):
    """Solo para Swagger: la misma respuesta que el login."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    usuario = UsuarioVerificadoSerializer()


def _clave_intentos(usuario):
    return f"2fa-verificar:intentos:{usuario.pk}"


def _clave_token_usado(token):
    return f"2fa-verificar:usado:{hashlib.sha256(token.encode()).hexdigest()}"


def _es_codigo_de_app(codigo):
    return len(codigo) == 6 and codigo.isdigit()


def _verificar_codigo_de_app(dispositivo, codigo):
    """Acepta el intervalo actual o uno de al lado (igual que valid_window=1), pero solo
    si es posterior al último que se usó; así el mismo código no sirve dos veces."""
    totp = pyotp.TOTP(dispositivo.secreto)
    actual = int(time.time() // PASO_TOTP)
    for intervalo in (actual - 1, actual, actual + 1):
        if not hmac.compare_digest(totp.at(intervalo * PASO_TOTP), codigo):
            continue
        if dispositivo.ultimo_intervalo is not None and intervalo <= dispositivo.ultimo_intervalo:
            return False
        dispositivo.ultimo_intervalo = intervalo
        dispositivo.save(update_fields=["ultimo_intervalo"])
        return True
    return False


class VerificarDosFactoresView(APIView):
    """POST /api/v1/auth/2fa/verificar/  {"token_temporal": "...", "codigo": "123456"}

    Es pública (AllowAny): el usuario todavía no tiene JWT; se identifica con el token temporal.
    """

    permission_classes = [AllowAny]
    # Pública: sin autenticadores, un Authorization inválido no responde 401 antes de validar el cuerpo
    authentication_classes = []

    def get_authenticate_header(self, request):
        # Sin autenticadores DRF cambiaría el 401 de token_invalido por 403;
        # se conserva el 401 igual que en la renovación de tokens (simplejwt)
        return 'Bearer realm="api"'

    @extend_schema(
        request=VerificarDosFactoresSerializer,
        responses={
            200: VerificarDosFactoresRespuestaSerializer,
            400: OpenApiResponse(
                description="datos_invalidos: faltan datos; codigo_invalido: código incorrecto, repetido o ya usado"
            ),
            401: OpenApiResponse(description="token_invalido: token temporal alterado, vencido, ya usado o sin 2FA"),
            429: OpenApiResponse(description="demasiados_intentos: más de 5 códigos incorrectos; incluye Retry-After"),
        },
        tags=["auth"],
        summary="Verificar el código 2FA y completar el inicio de sesión",
    )
    def post(self, request):
        serializer = VerificarDosFactoresSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token_temporal"]
        codigo = serializer.validated_data["codigo"].strip()

        usuario, recordarme = leer_token_temporal(token)
        metodo = "app" if _es_codigo_de_app(codigo) else "respaldo"

        # El bloqueo del dispositivo ordena las peticiones simultáneas del mismo usuario.
        # Las excepciones se lanzan fuera de la transacción para no deshacer el conteo de intentos.
        with transaction.atomic():
            dispositivo = Dispositivo2FA.objects.select_for_update().filter(usuario=usuario, confirmado=True).first()
            if dispositivo is None or cache.get(_clave_token_usado(token)):
                raise TokenInvalido()

            # Se guarda (intentos, cuándo vence el bloqueo) para responder Retry-After como en HU-24.
            intentos, vence = cache.get(_clave_intentos(usuario), (0, 0))
            bloqueado = intentos >= MAXIMO_INTENTOS
            valido = False
            if not bloqueado:
                if metodo == "app":
                    valido = _verificar_codigo_de_app(dispositivo, codigo)
                    # Un código de respaldo también puede ser de 6 números (por ejemplo 234-567 escrito sin guion)
                    if not valido and usar_codigo_respaldo(usuario, codigo):
                        valido, metodo = True, "respaldo"
                else:
                    valido = usar_codigo_respaldo(usuario, codigo)

                if valido:
                    cache.delete(_clave_intentos(usuario))
                    cache.set(_clave_token_usado(token), True, VIGENCIA_SEGUNDOS)
                    registrar_acceso(request, usuario, exitoso=True)  # t-22/st-167
                    usuario.last_login = timezone.now()
                    usuario.save(update_fields=["last_login"])
                else:
                    intentos += 1
                    vence = time.time() + VIGENCIA_SEGUNDOS
                    cache.set(_clave_intentos(usuario), (intentos, vence), VIGENCIA_SEGUNDOS)
                    registrar_acceso(request, usuario, exitoso=False)  # t-22/st-167

        if bloqueado:
            registrar_evento("login_2fa_bloqueado", usuario, request, resultado="error")
            raise Throttled(wait=max(1, int(vence - time.time())))
        if not valido:
            registrar_evento("login_2fa_fallido", usuario, request, resultado="error", metodo=metodo, intentos=intentos)
            raise CodigoInvalido()

        registrar_evento("login_2fa_completado", usuario, request, metodo=metodo)
        return Response(emitir_jwt(usuario, recordarme))