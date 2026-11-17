from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from comun.errores import CredencialesInvalidas, CuentaPendiente, CuentaInactiva
from usuarios.models import Estado

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # 1. Sobrescribimos el get_token original para agregar los claims
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregamos los claims al token
        token['rol'] = user.rol
        token['email_verificado'] = user.email_verificado
        token['token_version'] = user.token_version
        token['debe_cambiar_password'] = user.debe_cambiar_password
        return token

    def validate(self, attrs):
        # 2. Usamos authenticate manual para controlar los errores
        identificador = attrs.get('email') or attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(request=self.context.get('request'), username=identificador, password=password)

        # 3. Lanzamos nuestros propios errores en español
        if not user:
            raise CredencialesInvalidas()
        
        if user.estado == Estado.PENDIENTE:
            raise CuentaPendiente()
            
        if user.estado == Estado.INACTIVO:
            raise CuentaInactiva()

        # 4. Actualizamos el último acceso
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # 5. Generamos el token usando el get_token que modificamos arriba
        refresh = self.get_token(user)
        
        data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'id': str(user.id),
                'nombre': user.first_name,
                'email': user.email,
                'rol': user.rol,
            }
        }
        return data