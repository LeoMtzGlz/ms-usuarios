from datetime import timedelta
from uuid import UUID

from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch
from rest_framework_simplejwt.exceptions import TokenError

from comun.errores import CredencialesInvalidas, CuentaPendiente, CuentaInactiva, TokenInvalido

from usuarios.models import Estado
from usuarios.accesos import buscar_usuario, registrar_acceso  # t-22/st-167

# t-06/st-85 - HU-06: "con recordarme la renovación dura 7 días; sin él, 1 día"
DURACION_REFRESH_CON_RECORDARME = timedelta(days=7)
DURACION_REFRESH_SIN_RECORDARME = timedelta(days=1)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    recordarme = serializers.BooleanField(required=False, default=False)  # t-06/st-85

    # 1. Sobrescribimos el get_token original para agregar los claims
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregamos los claims al token
        token['rol'] = user.rol
        token['email_verificado'] = user.email_verificado
        token['token_version'] = user.token_version
        token['debe_cambiar_password'] = user.debe_cambiar_password
        token['zona_id'] = user.zona_id
        return token

    def validate(self, attrs):
        # 2. Usamos authenticate manual para controlar los errores
        identificador = attrs.get('email') or attrs.get('username')
        password = attrs.get('password')
        
        request = self.context.get('request')
        user = authenticate(request=request, username=identificador, password=password)

        # 3. Lanzamos nuestros propios errores en español
        if not user:
            registrar_acceso(request, buscar_usuario(identificador), exitoso=False)  # t-22/st-167
            raise CredencialesInvalidas()
        
        if user.estado == Estado.PENDIENTE:
            registrar_acceso(request, user, exitoso=False)  # t-22/st-167
            raise CuentaPendiente()
            
        if user.estado == Estado.INACTIVO:
            registrar_acceso(request, user, exitoso=False)  # t-22/st-167
            raise CuentaInactiva()

        registrar_acceso(request, user, exitoso=True)  # t-22/st-167

        # 4. Actualizamos el último acceso
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # 5. Generamos el token usando el get_token que modificamos arriba
        refresh = self.get_token(user)

        # t-06/st-85: la vida del refresh depende de "recordarme"; el access sigue en 15 min
        recordarme = attrs.get('recordarme', False)
        refresh.set_exp(
            lifetime=DURACION_REFRESH_CON_RECORDARME if recordarme else DURACION_REFRESH_SIN_RECORDARME
        )
        # El serializer de renovación de ST-90 debe leer este claim para conservar la
        # duración al rotar; si no, el refresh rotado tomaría REFRESH_TOKEN_LIFETIME (7 días)
        refresh['recordarme'] = recordarme
        # for_user() ya registró el OutstandingToken con el exp de 7 días (token_blacklist, ST-89);
        # se alinea con el exp nuevo para que la limpieza de vencidos (ST-91) sea correcta
        OutstandingToken.objects.filter(jti=refresh[api_settings.JTI_CLAIM]).update(
            expires_at=datetime_from_epoch(refresh['exp'])
        )

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

# t-07/st-90: Serializer propio para la renovación de tokens JWT
class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Renueva los tokens validando el estado actual del usuario."""

    # t-07/st-90: Ejecutar la validación y rotación en una transacción.
    @transaction.atomic
    def validate(self, attrs):
        # t-07/st-90: Validar el refresh recibido.
        refresh = self.token_class(attrs["refresh"])

        # Obtener el identificador del usuario desde el token.
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)

        if not user_id:
            raise TokenInvalido()

        # t-07/st-90: Validar el UUID antes de consultar PostgreSQL.
        try:
            user_id = UUID(str(user_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TokenInvalido() from exc

        # t-07/st-90: Serializar renovaciones concurrentes del mismo usuario.
        usuario = (get_user_model().objects.select_for_update().filter(pk=user_id).first())

        if usuario is None:
            raise TokenInvalido()

        # t-07/st-90: Volver a verificar el refresh después de adquirir el bloqueo.
        try:
            refresh.check_blacklist()
        except TokenError as exc:
            raise TokenInvalido() from exc

        # t-07/st-90: Solo las cuentas activas pueden renovar.
        if usuario.estado != Estado.ACTIVO or not usuario.is_active:
            raise TokenInvalido()

        # Comprobar que el token pertenece a la versión de sesión vigente.
        if refresh.payload.get("token_version") != usuario.token_version:
            raise TokenInvalido()

        # t-07/st-90: Actualizar los claims con los datos vigentes del usuario.
        refresh["rol"] = usuario.rol
        refresh["email_verificado"] = usuario.email_verificado
        refresh["token_version"] = usuario.token_version
        refresh["debe_cambiar_password"] = usuario.debe_cambiar_password
        refresh["zona_id"] = usuario.zona_id

        # t-07/st-90: Generar el access con los claims actualizados.
        access = str(refresh.access_token)

        # Conservar la duración elegida al iniciar sesión.
        recordarme = refresh.payload.get("recordarme", False)

        duracion = (
            DURACION_REFRESH_CON_RECORDARME
            if recordarme
            else DURACION_REFRESH_SIN_RECORDARME
        )

        # t-07/st-90: Invalidar el refresh anterior.
        refresh.blacklist()

        # Generar una nueva identidad y fecha de emisión.
        refresh.set_jti()
        refresh.set_iat()

        # Establecer la duración correspondiente a "recordarme".
        refresh.set_exp(lifetime=duracion)
        refresh["recordarme"] = recordarme

        # Registrar el nuevo refresh en OutstandingToken.
        refresh.outstand()

        return {
            "access": access,
            "refresh": str(refresh),
        }