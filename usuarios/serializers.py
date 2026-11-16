from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.utils import timezone
from comun.errores import CuentaPendiente, CuentaInactiva

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Llama al validate original (verifica credenciales y busca al usuario)
        data = super().validate(attrs)
        
        # 2. Revisar el estado de la cuenta
        if self.user.estado == 'pendiente':
            raise CuentaPendiente()
        if self.user.estado == 'inactivo':
            raise CuentaInactiva()

        # 3. Actualizar el último acceso (last_login)
        self.user.last_login = timezone.now()
        self.user.save(update_fields=['last_login'])

        # 4. Obtener el token
        token = self.get_token(self.user)
        
        # 5. Agregar los claims
        token['rol'] = self.user.rol
        token['email_verificado'] = self.user.email_verificado
        token['token_version'] = self.user.token_version
        token['debe_cambiar_password'] = self.user.debe_cambiar_password

        # 6. Estructurar la respuesta (sobrescribiendo el access y refresh con los claims nuevos)
        data['access'] = str(token.access_token)
        data['refresh'] = str(token)
        
        # 7. Datos extra del usuario para el frontend
        data['usuario'] = {
            'id': str(self.user.id),
            'nombre': self.user.first_name,
            'email': self.user.email,
            'rol': self.user.rol,
        }

        return data