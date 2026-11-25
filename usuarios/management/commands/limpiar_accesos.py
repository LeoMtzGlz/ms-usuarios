"""t-22/st-169 (HU-22): borrar a mano los registros de acceso viejos.

    python manage.py limpiar_accesos            # más de 90 días
    python manage.py limpiar_accesos --dias 30  # más de 30 días
"""
from django.core.management.base import BaseCommand, CommandError

from usuarios.limpieza import DIAS_POR_DEFECTO, limpiar_accesos_viejos


class Command(BaseCommand):
    help = "Borra los registros de acceso con más de N días (90 por defecto)."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=DIAS_POR_DEFECTO,
                            help="Antigüedad en días (90 por defecto).")

    def handle(self, *args, **opciones):
        dias = opciones["dias"]
        if dias < 1:
            raise CommandError("--dias debe ser 1 o más")
        borrados = limpiar_accesos_viejos(dias=dias)
        self.stdout.write(f"{borrados} registros de acceso borrados (más de {dias} días)")