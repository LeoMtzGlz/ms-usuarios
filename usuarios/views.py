"""Vistas de la app usuarios."""
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
from usuarios.models import Proposito
from usuarios.serializers import RegistroSerializer


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


class CustomTokenObtainPairView(TokenObtainPairView):
    """HU-05 / ST-82: POST /api/v1/auth/login/"""
    serializer_class = CustomTokenObtainPairSerializer


# ==========================================
# Vistas para HU-29 (Aviso de Privacidad) - t-29/st-201
# ==========================================
class PrivacidadInfoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # t-29/st-201: Permite acceso público incluso con tokens expirados
    
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