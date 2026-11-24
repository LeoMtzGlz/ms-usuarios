from django.db import transaction
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# --- Imports para el Login (ST-82) ---
from rest_framework_simplejwt.views import TokenObtainPairView
from usuarios.tokens import CustomTokenObtainPairSerializer

from comun.eventos import registrar_evento
from usuarios.codigos import generar_codigo
from usuarios.models import Canal, Estado, Proposito
from usuarios.serializers import ActivarSerializer, RegistroSerializer

class RegistroView(APIView):
    """HU-02 / ST-66: POST /api/v1/auth/registro/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=RegistroSerializer, responses={201: RegistroSerializer}, tags=["auth"])
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            usuario = serializer.save()
            generar_codigo(usuario, Proposito.ACTIVACION)

        registrar_evento("registro", usuario, request, canal=usuario.canal_preferido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ActivarCuentaView(APIView):
    """HU-03 / ST-72: POST /api/v1/auth/activar/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=ActivarSerializer, responses={200: ActivarSerializer}, tags=["auth"])
    def post(self, request):
        serializer = ActivarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data["usuario"]
        registro = serializer.validated_data["registro_codigo"]

        usuario.estado = Estado.ACTIVO
        if registro.canal == Canal.CORREO:
            usuario.email_verificado = True
        elif registro.canal == Canal.WHATSAPP:
            usuario.telefono_verificado = True
        usuario.save(update_fields=["estado", "email_verificado", "telefono_verificado"])

        return Response(
            {
                "id": str(usuario.id),
                "correo": usuario.email,
                "estado": usuario.estado,
                "mensaje": "Cuenta activada.",
            },
            status=status.HTTP_200_OK,
        )

class CustomTokenObtainPairView(TokenObtainPairView):
    """HU-05 / ST-82: POST /api/v1/auth/login/"""
    serializer_class = CustomTokenObtainPairSerializer

class PrivacidadInfoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["Privacidad"], summary="Obtener la versión vigente del aviso de privacidad", responses={200: OpenApiResponse(description="Versión y URL del aviso")})
    def get(self, request):
        return Response({
            "version": settings.VERSION_AVISO_PRIVACIDAD,
            "url": settings.URL_AVISO_PRIVACIDAD
        })

class AceptarPrivacidadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Privacidad"], summary="Aceptar el aviso de privacidad", responses={200: OpenApiResponse(description="Aviso aceptado correctamente")})
    def post(self, request):
        user = request.user
        user.version_privacidad = settings.VERSION_AVISO_PRIVACIDAD
        user.acepto_privacidad_en = timezone.now()
        user.save(update_fields=['version_privacidad', 'acepto_privacidad_en'])
        registrar_evento("privacidad_aceptada", user, request, version=user.version_privacidad)
        return Response({
            "mensaje": "Aviso de privacidad aceptado correctamente.",
            "version": user.version_privacidad
        })