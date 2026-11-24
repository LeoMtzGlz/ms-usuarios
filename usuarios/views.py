from django.db import transaction
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# --- Imports para el Login (ST-82) ---
from rest_framework_simplejwt.views import TokenObtainPairView
from usuarios.tokens import CustomTokenObtainPairSerializer


from comun.eventos import registrar_evento
from usuarios.codigos import generar_codigo
from usuarios.models import Canal, Proposito
from usuarios.serializers import RegistroSerializer, CambiarPasswordSerializer


class RegistroRespuestaSerializer(RegistroSerializer):
    """Solo documenta el 201 (OpenAPI); la vista arma el cuerpo a mano."""

    canal_codigo = serializers.ChoiceField(choices=Canal.choices, help_text="Canal por el que salió el código")
    canal_sustituido = serializers.BooleanField(help_text="true si no es el canal preferido")


class RegistroView(APIView):
    """HU-02 / ST-66: POST /api/v1/auth/registro/

    Crea la cuenta (pendiente, rol cliente) y encola el código de activación.
    Todo ocurre en una sola transacción: si falla el código o la notificación,
    la cuenta tampoco se crea. Responde 201 sin tokens: la sesión se inicia
    hasta que la cuenta se active (HU-03).

    HU-01 / ST-61: además de los datos de la cuenta, informa `canal_codigo`
    (por dónde salió el código) y `canal_sustituido` (true si no es el canal
    preferido, p. ej. WhatsApp sin teléfono sale por correo).
    """

    # t-24/st-179: Limitar el registro a 5 solicitudes por hora por IP
    throttle_scope = "registro"

    permission_classes = [AllowAny]
    authentication_classes = []  # registro público: un token viejo o inválido no debe dar 401

    @extend_schema(
        request=RegistroSerializer,
        responses={201: RegistroRespuestaSerializer},
        tags=["auth"],
    )
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            usuario = serializer.save()  # Usuario.objects.create_user(...)
            registro = generar_codigo(usuario, Proposito.ACTIVACION)

        registrar_evento("registro", usuario, request, canal=usuario.canal_preferido)
        # No replicar este aviso en la recuperación de contraseña (HU-10): revelaría si la cuenta existe.
        cuerpo = {
            **serializer.data,
            "canal_codigo": str(registro.canal),
            "canal_sustituido": str(registro.canal) != str(usuario.canal_preferido),
        }
        return Response(cuerpo, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """HU-05 / ST-82: POST /api/v1/auth/login/"""
    serializer_class = CustomTokenObtainPairSerializer


# ==========================================
# Vistas para HU-29 (Aviso de Privacidad) - t-29/st-201
# ==========================================
class PrivacidadInfoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(
        tags=["Privacidad"],
        summary="Obtener la versión vigente del aviso de privacidad",
        responses={200: OpenApiResponse(description="Versión y URL del aviso")}
    )
    def get(self, request):
        return Response({
            "version": settings.VERSION_AVISO_PRIVACIDAD,
            "url": settings.URL_AVISO_PRIVACIDAD
        })

class AceptarPrivacidadView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Privacidad"],
        summary="Aceptar el aviso de privacidad",
        responses={200: OpenApiResponse(description="Aviso aceptado correctamente")}
    )
    def post(self, request):
        user = request.user
        user.version_privacidad = settings.VERSION_AVISO_PRIVACIDAD
        user.acepto_privacidad_en = timezone.now()
        user.save(update_fields=['version_privacidad', 'acepto_privacidad_en'])
        
        # t-29/st-201: Registro en la bitácora
        registrar_evento("privacidad_aceptada", user, request, version=user.version_privacidad)
        
        return Response({
            "mensaje": "Aviso de privacidad aceptado correctamente.",
            "version": user.version_privacidad
        })

# ==========================================
# HU-11 / ST-112: Cambiar mi contraseña
# ==========================================
class CambiarPasswordView(APIView):
    """POST /api/v1/auth/cambiar-password/

    Usuario autenticado envía contraseña actual + nueva + confirmación.
    Valida con los validadores de Django, aplica Usuario.cambiar_password()
    (marca definitiva, incrementa token_version y registra el evento).

    Solo exige IsAuthenticated: debe funcionar también con contraseña temporal
    (ContrasenaDefinitiva no aplica aquí; ver ST-116).

    La emisión de tokens nuevos corresponde a ST-113.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CambiarPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Contraseña actualizada correctamente"),
            400: OpenApiResponse(description="Datos inválidos o contraseña actual incorrecta"),
            401: OpenApiResponse(description="No autenticado"),
        },
        tags=["auth"],
        summary="Cambiar la contraseña del usuario autenticado",
    )
    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"mensaje": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )

