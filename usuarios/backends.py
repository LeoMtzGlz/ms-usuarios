from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from usuarios.telefono import normalizar_telefono

Usuario = get_user_model()

class EmailOrPhoneBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # SimpleJWT lo llama con email=, Django normal lo llama con username=
        username = username or kwargs.get("email")
        
        if username is None or password is None:
            return None
        
        # 1. Intentar buscar por correo (sin importar mayúsculas)
        try:
            usuario = Usuario.objects.get(email__iexact=username)
        except Usuario.DoesNotExist:
            # 2. Si no es correo, intentar normalizar y buscar por teléfono
            try:
                telefono_norm = normalizar_telefono(username)
                usuario = Usuario.objects.get(telefono=telefono_norm)
            except (Usuario.DoesNotExist, ValidationError):
                # 3. Si no existe, calculamos un hash falso para que tarde lo mismo
                # y no se pueda adivinar qué correos están registrados.
                Usuario().set_password(password)
                return None
        
        # 4. Verificar contraseña
        if usuario.check_password(password):
            return usuario
            
        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None