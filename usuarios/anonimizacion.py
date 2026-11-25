"""HU-23 / ST-173: anonimizar la cuenta de un usuario.

Aplica el contrato de docs/HU-23/ST-172-datos-anonimizados.md:
- nombre, correo y teléfono se reemplazan por valores genéricos (únicos donde la base lo exige);
- la contraseña queda inutilizable (set_unusable_password);
- la cuenta queda inactiva y se cierran todas sus sesiones;
- se borran las credenciales (códigos, 2FA) y los datos que guardan el correo en texto (django-axes);
- se conservan id, rol, fechas, aceptación de privacidad, historial de accesos y bitácora.

No valida la contraseña, la palabra ELIMINAR ni la regla del único administrador, y no
encola el correo de confirmación: eso lo hace el endpoint (ST-174) antes de llamarla.
"""
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from comun.eventos import registrar_evento
from notificaciones.models import Notificacion
from usuarios.models import Canal, CodigoVerificacion, Dispositivo2FA, Estado

NOMBRE_ANONIMO = "Usuario"
APELLIDO_ANONIMO = "eliminado"
DOMINIO_ANONIMO = "anonimo.invalid"  # dominio reservado (RFC 2606): nunca recibe correo


def correo_anonimo(usuario) -> str:
    """Correo genérico y único: usa el id, que nunca cambia ni se repite."""
    return f"eliminado-{usuario.pk}@{DOMINIO_ANONIMO}"


def esta_anonimizado(usuario) -> bool:
    return usuario.email == correo_anonimo(usuario)


@transaction.atomic
def anonimizar_usuario(usuario, *, request=None, conservar_notificaciones=()) -> None:
    """Anonimiza la cuenta en una sola transacción. Es irreversible.

    conservar_notificaciones: ids de notificaciones que no se tocan, por ejemplo el
    correo de confirmación que ST-174 encola justo antes de llamar a esta función.
    """
    if esta_anonimizado(usuario):
        return  # ya estaba anonimizada: no repetir eventos ni cambios

    correo_original = usuario.email

    # Credenciales: ya no sirven y podrían reactivar o recuperar la cuenta
    CodigoVerificacion.objects.filter(usuario=usuario).delete()
    Dispositivo2FA.objects.filter(usuario=usuario).delete()

    # Notificaciones: pendientes fuera, las demás sin el contenido del mensaje
    notificaciones = Notificacion.objects.filter(destinatario=usuario).exclude(pk__in=conservar_notificaciones)
    notificaciones.filter(estado=Notificacion.ESTADO_PENDIENTE).delete()
    notificaciones.update(contexto={})

    # django-axes guarda el correo escrito en texto, sin relación con el usuario
    for modelo in (AccessAttempt, AccessFailureLog, AccessLog):
        modelo.objects.filter(username__iexact=correo_original).delete()

    # Sesiones: todo refresh token del usuario a la lista negra
    pendientes = OutstandingToken.objects.filter(user=usuario, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=token) for token in pendientes])

    # Datos personales del usuario
    usuario.email = correo_anonimo(usuario)
    usuario.telefono = None
    usuario.first_name = NOMBRE_ANONIMO
    usuario.last_name = APELLIDO_ANONIMO
    usuario.set_unusable_password()
    usuario.email_verificado = False
    usuario.telefono_verificado = False
    usuario.canal_preferido = Canal.CORREO
    usuario.debe_cambiar_password = False
    usuario.is_staff = False
    usuario.is_superuser = False
    usuario.save(
        update_fields=[
            "email", "telefono", "first_name", "last_name", "password",
            "email_verificado", "telefono_verificado", "canal_preferido",
            "debe_cambiar_password", "is_staff", "is_superuser",
        ]
    )
    usuario.groups.clear()
    usuario.user_permissions.clear()

    # inactivo + is_active=False + token_version += 1 (cierra los access tokens)
    usuario.cambiar_estado(Estado.INACTIVO, por=usuario)

    registrar_evento("cuenta_anonimizada", usuario, request)