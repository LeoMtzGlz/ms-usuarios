from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from user_agents import parse
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Lógica base de SimpleJWT (valida email y contraseña)
        data = super().validate(attrs)
        user = self.user
        
        # ==========================================
        # HU-28: Detección de dispositivo nuevo
        # ==========================================
        request = self.context.get('request')
        if request:
            user_agent_string = request.META.get('HTTP_USER_AGENT', '')
            user_agent = parse(user_agent_string)
            dispositivo_actual = f"{user_agent.browser.family} en {user_agent.os.family}"
            
            # Validación defensiva (por si RegistroAcceso no existe aún)
            registros_acceso = getattr(user, 'registros_acceso', None)
            
            if registros_acceso and registros_acceso.count() > 0:
                hace_90_dias = timezone.now() - timedelta(days=90)
                historial = registros_acceso.filter(
                    fecha__gte=hace_90_dias,
                    dispositivo__icontains=user_agent.browser.family
                )
                
                if not historial.exists():
                    try:
                        from notificaciones.services import notificar
                        contexto = {
                            'fecha': timezone.now().strftime('%Y-%m-%d %H:%M'),
                            'dispositivo': dispositivo_actual,
                            'ip': request.META.get('REMOTE_ADDR')
                        }
                        notificar(usuario=user, plantilla='dispositivo_nuevo', contexto=contexto, canal='correo')
                    except ImportError:
                        pass # Si notificar() no existe aún, no truena el login

        # ==========================================
        # HU-29: Validar Aviso de Privacidad
        # ==========================================
        version_actual = getattr(settings, 'VERSION_AVISO_PRIVACIDAD', '2026-10')
        data['requiere_aceptar_privacidad'] = user.version_privacidad != version_actual
        
        return data