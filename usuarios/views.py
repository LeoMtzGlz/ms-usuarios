from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

# Importamos el serializer que acabamos de crear
from .serializers import CustomTokenObtainPairSerializer

# ==========================================
# Vista de Login personalizada
# ==========================================
@extend_schema(tags=["Autenticación"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ==========================================
# Vistas para HU-29 (Aviso de Privacidad)
# ==========================================
class PrivacidadInfoView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["Privacidad"],
        summary="Obtener la versión vigente del aviso de privacidad",
        description="Devuelve la versión actual del aviso y la URL donde se puede leer.",
        responses={
            200: OpenApiResponse(
                description="Versión y URL del aviso de privacidad",
                response={"version": "2026-10", "url": "https://..."}
            )
        }
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
        description="Registra la fecha y la versión vigente como aceptadas por el usuario autenticado.",
        responses={
            200: OpenApiResponse(
                description="Aviso aceptado correctamente",
                response={"mensaje": "Aviso de privacidad aceptado correctamente.", "version": "2026-10"}
            ),
            401: OpenApiResponse(description="No autenticado (falta token)")
        }
    )
    def post(self, request):
        user = request.user
        user.version_privacidad = settings.VERSION_AVISO_PRIVACIDAD
        user.acepto_privacidad_en = timezone.now()
        user.save(update_fields=['version_privacidad', 'acepto_privacidad_en'])
        
        return Response({
            "mensaje": "Aviso de privacidad aceptado correctamente.",
            "version": user.version_privacidad
        })