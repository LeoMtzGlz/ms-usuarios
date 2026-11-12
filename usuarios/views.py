from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.utils import timezone

# Importamos el serializer que acabamos de crear
from .serializers import CustomTokenObtainPairSerializer

# Vista de Login personalizada (Para usar tu serializer con la HU-28 y HU-29)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ==========================================
# Vistas para HU-29 (Aviso de Privacidad)
# ==========================================
class PrivacidadInfoView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            "version": settings.VERSION_AVISO_PRIVACIDAD,
            "url": settings.URL_AVISO_PRIVACIDAD
        })

class AceptarPrivacidadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        user.version_privacidad = settings.VERSION_AVISO_PRIVACIDAD
        user.acepto_privacidad_en = timezone.now()
        user.save(update_fields=['version_privacidad', 'acepto_privacidad_en'])
        
        return Response({
            "mensaje": "Aviso de privacidad aceptado correctamente.",
            "version": user.version_privacidad
        })