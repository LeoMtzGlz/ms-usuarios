"""t-33/st-219 (HU-33): iniciar sesión con Google.

El frontend obtiene un ID token con el botón de Google y lo manda aquí. El backend:
1. lo verifica con google.oauth2.id_token.verify_oauth2_token contra GOOGLE_CLIENT_ID (st-218);
2. si el correo ya existe, inicia sesión con esa cuenta (se vincula); si no, crea un Cliente
   sin contraseña usable y con el correo verificado;
3. termina igual que el login con contraseña (completar_login): mismos JWT y 2FA si aplica.
"""
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from comun.errores import CuentaInactiva, GoogleNoConfigurado, TokenGoogleInvalido
from comun.eventos import registrar_evento
from comun.roles import Rol
from usuarios.accesos import registrar_acceso
from usuarios.models import Canal, CodigoVerificacion, Estado, Usuario
from usuarios.privacidad import datos_aceptacion_privacidad

logger = logging.getLogger(__name__)


def verificar_id_token(token: str) -> dict:
    """Devuelve los datos del ID token si Google lo firmó para NUESTRA app y no ha vencido.

    Sin GOOGLE_CLIENT_ID no se verifica nada: verify_oauth2_token con audience vacío
    aceptaría tokens emitidos para cualquier otra app.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleNoConfigurado()
    try:
        datos = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except google_exceptions.TransportError as error:
        # No se pudieron descargar las llaves públicas de Google: no es culpa del token
        logger.warning("No se pudo consultar a Google para verificar el ID token: %s", error)
        raise GoogleNoConfigurado() from error
    except (ValueError, google_exceptions.GoogleAuthError) as error:
        # Firma, audiencia (aud), emisor (iss) o vigencia (exp) incorrectos
        raise TokenGoogleInvalido() from error

    if not datos.get("email") or datos.get("email_verified") is not True:
        raise TokenGoogleInvalido()
    return datos


def obtener_o_crear_usuario(datos: dict, request=None, acepto_privacidad: bool = False):
    """Devuelve (usuario, creado). Vincula por correo o crea un Cliente nuevo.

    - Cuenta existente activa: se usa tal cual.
    - Cuenta existente pendiente: Google ya verificó el correo, así que se activa.
    - Correo no verificado (pendiente o no): se anulan contraseña, teléfono no verificado,
      códigos y sesiones de quien lo registró (anular_credenciales_no_verificadas).
    - Cuenta existente inactiva: no entra (403 cuenta_inactiva), igual que con contraseña.
    - Correo nuevo: Cliente activo, sin contraseña usable y con email_verificado=True.
    """
    correo = datos["email"].strip().lower()
    usuario = Usuario.objects.filter(email__iexact=correo).first()

    if usuario is None:
        try:
            with transaction.atomic():
                usuario = Usuario.objects.create_user(
                    email=correo,
                    password=None,  # set_password(None) deja la contraseña inutilizable
                    first_name=datos.get("given_name", "")[:150],
                    last_name=datos.get("family_name", "")[:150],
                    rol=Rol.CLIENTE,
                    estado=Estado.ACTIVO,
                    email_verificado=True,
                    canal_preferido=Canal.CORREO,
                    **(datos_aceptacion_privacidad() if acepto_privacidad else {}),
                )
        except IntegrityError:
            # Dos primeros inicios de sesión al mismo tiempo: el otro ya la creó
            usuario = Usuario.objects.get(email__iexact=correo)
        else:
            registrar_evento("cuenta_creada_con_google", usuario, request)
            return usuario, True

    if usuario.estado == Estado.INACTIVO:
        registrar_acceso(request, usuario, exitoso=False)
        raise CuentaInactiva()

    if not usuario.email_verificado:
        anular_credenciales_no_verificadas(usuario, request)

    if usuario.estado == Estado.PENDIENTE:
        usuario.cambiar_estado(Estado.ACTIVO, por=usuario)

    registrar_evento("cuenta_vinculada_con_google", usuario, request)
    return usuario, False


def anular_credenciales_no_verificadas(usuario, request=None):
    """El correo no estaba verificado: quien lo registró no demostró ser su dueño.

    Evita la "toma de cuenta anticipada": alguien registra el correo de otra persona con
    su propia contraseña (y su teléfono) y espera a que la víctima entre con Google.
    Google sí demostró que el correo es de quien está entrando, así que se anula todo lo
    que dejó quien lo registró:
    - la contraseña (set_unusable_password);
    - el teléfono si no estaba verificado, porque la recuperación (HU-10) acepta el teléfono;
    - los códigos de activación o recuperación pendientes;
    - las sesiones: token_version += 1 y refresh tokens a la lista negra.
    """
    usuario.set_unusable_password()
    usuario.email_verificado = True
    usuario.token_version += 1
    campos = ["password", "email_verificado", "token_version"]
    if not usuario.telefono_verificado:
        usuario.telefono = None
        usuario.canal_preferido = Canal.CORREO
        campos += ["telefono", "canal_preferido"]
    usuario.save(update_fields=campos)

    CodigoVerificacion.objects.filter(usuario=usuario).delete()
    pendientes = OutstandingToken.objects.filter(user=usuario, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=token) for token in pendientes])

    registrar_evento("credenciales_no_verificadas_anuladas", usuario, request)