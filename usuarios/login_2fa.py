"""t-31/st-210: token temporal del login con 2FA (HU-31).

Si el usuario tiene el 2FA confirmado, el login no entrega los JWT: entrega un token
temporal de 5 minutos que solo sirve para completar el inicio de sesión en
POST /api/v1/auth/2fa/verificar/ (st-211).

El token se firma con TimestampSigner y un salt propio, así que no sirve como JWT
ni para ninguna otra firma del proyecto. Lleva el id del usuario, su token_version
y la opción "recordarme" del login (st-85): si cierra todas sus sesiones o cambia su
contraseña dentro de esos 5 minutos, el token temporal deja de servir, y la st-211
emite el refresh con la duración que el usuario eligió.
"""

from django.contrib.auth import get_user_model
from django.core import signing

from comun.errores import TokenInvalido
from usuarios.models import Dispositivo2FA, Estado

SALT = "ms-usuarios.login-2fa"
VIGENCIA_SEGUNDOS = 300  # 5 minutos (HU-31, criterio 1)


def tiene_2fa_activo(usuario) -> bool:
    """True solo si el usuario ya confirmó su 2FA (un dispositivo sin confirmar no cuenta)."""
    return Dispositivo2FA.objects.filter(usuario=usuario, confirmado=True).exists()


def emitir_token_temporal(usuario, recordarme: bool = False) -> str:
    firmador = signing.TimestampSigner(salt=SALT)
    return firmador.sign_object({"uid": str(usuario.pk), "tv": usuario.token_version, "rec": bool(recordarme)})


def leer_token_temporal(token: str):
    """Devuelve (usuario, recordarme) del token temporal o lanza TokenInvalido. La usará st-211.

    Rechaza el token si está alterado, si se firmó con otro salt, si pasaron más de
    5 minutos, si la cuenta ya no está activa o si cambió su token_version.
    """
    firmador = signing.TimestampSigner(salt=SALT)
    try:
        datos = firmador.unsign_object(token, max_age=VIGENCIA_SEGUNDOS)
    except signing.BadSignature as error:  # incluye SignatureExpired
        raise TokenInvalido() from error

    usuario = get_user_model().objects.filter(pk=datos.get("uid")).first()
    if usuario is None or usuario.estado != Estado.ACTIVO or usuario.token_version != datos.get("tv"):
        raise TokenInvalido()
    return usuario, bool(datos.get("rec", False))
