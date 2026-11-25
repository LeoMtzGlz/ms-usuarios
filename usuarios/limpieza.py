"""t-22/st-169 (HU-22): borrar los registros de acceso de más de 90 días.

- ``limpiar_accesos_viejos()``  borra por lotes y devuelve cuántos borró.
- ``limpiar_si_toca()``         la llama el worker cada ciclo, pero solo limpia si ya
                                pasaron 24 h desde la última vez (fila ControlLimpieza).
- Comando a mano:               python manage.py limpiar_accesos [--dias 90]
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from usuarios.models import ControlLimpieza, RegistroAcceso

logger = logging.getLogger("svc.usuarios")

DIAS_POR_DEFECTO = 90
TAMANO_LOTE_BORRADO = 1000
CADA_CUANTO = timedelta(hours=24)
NOMBRE_TAREA = "limpiar_accesos"


def limpiar_accesos_viejos(dias=DIAS_POR_DEFECTO, ahora=None, tamano_lote=TAMANO_LOTE_BORRADO):
    """Borra los accesos con fecha anterior a ``ahora - dias``. Devuelve cuántos borró.

    Un registro de exactamente 90 días (fecha == límite) se queda: se borra lo que tiene
    *más* de 90 días. Se borra por lotes para no bloquear la tabla si hay muchos.
    """
    if dias < 1:
        raise ValueError("dias debe ser 1 o más")
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(days=dias)

    total = 0
    while True:
        ids = list(
            RegistroAcceso.objects.filter(fecha__lt=limite)
            .order_by("id")
            .values_list("id", flat=True)[:tamano_lote]
        )
        if not ids:
            break
        borrados, _ = RegistroAcceso.objects.filter(id__in=ids).delete()
        total += borrados

    logger.info("Limpieza de accesos: %s registros de más de %s días borrados", total, dias)
    return total


def limpiar_si_toca(ahora=None):
    """Limpia solo si pasaron 24 h desde la última vez. Devuelve cuántos borró, o None si no tocaba.

    Con varios workers: el que bloquea la fila limpia; los demás se la saltan
    (skip_locked) y vuelven a intentar en su siguiente ciclo, cuando ya no toca.
    """
    ahora = ahora or timezone.now()
    ControlLimpieza.objects.get_or_create(nombre=NOMBRE_TAREA)
    with transaction.atomic():
        control = (
            ControlLimpieza.objects.select_for_update(skip_locked=True)
            .filter(nombre=NOMBRE_TAREA)
            .first()
        )
        if control is None:  # otro worker la está corriendo ahora mismo
            return None
        if control.ultima_ejecucion and ahora - control.ultima_ejecucion < CADA_CUANTO:
            return None
        borrados = limpiar_accesos_viejos(ahora=ahora)
        control.ultima_ejecucion = ahora
        control.save(update_fields=["ultima_ejecucion"])
    return borrados