"""¿Qué cuentas están bloqueadas ahora por intentos fallidos? (HU-16 / ST-145)

django-axes guarda un AccessAttempt por cada combinación bloqueada. Una cuenta se considera
bloqueada si tiene algún intento con al menos AXES_FAILURE_LIMIT fallos y todavía dentro del
tiempo de espera (AXES_COOLOFF_TIME). El intento se asocia a la cuenta por el `username` que
guardó Axes: el correo (sin importar mayúsculas) o el teléfono en formato E.164.
"""
from axes.helpers import get_cool_off
from axes.models import AccessAttempt
from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Lower
from django.utils import timezone


def con_bloqueada(usuarios):
    """Agrega `bloqueada` (bool) a cada usuario con una sola consulta, sin N+1."""
    intentos = (
        AccessAttempt.objects.annotate(identificador=Lower("username"))
        .filter(failures_since_start__gte=settings.AXES_FAILURE_LIMIT)
        .filter(Q(identificador=OuterRef("email")) | Q(username=OuterRef("telefono")))
    )
    espera = get_cool_off()  # timedelta, o None si el bloqueo no vence
    if espera is not None:
        intentos = intentos.filter(attempt_time__gte=timezone.now() - espera)
    return usuarios.annotate(bloqueada=Exists(intentos))
