"""t-10/st-51: worker de la bandeja de salida.

    python manage.py procesar_notificaciones            # bucle: cada 5 s, lotes de 20
    python manage.py procesar_notificaciones --una-vez  # un solo lote y termina

Sin Redis ni Celery: lee la tabla Notificacion de PostgreSQL. Se puede correr más de un
worker a la vez; select_for_update(skip_locked=True) evita que envíen la misma.
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from notificaciones import worker

logger = logging.getLogger("svc.notificaciones")


class Command(BaseCommand):
    help = "Envía las notificaciones pendientes cada 5 s en lotes de 20."

    def add_arguments(self, parser):
        parser.add_argument("--una-vez", action="store_true", help="Procesa un solo lote y termina.")
        parser.add_argument("--intervalo", type=float, default=worker.INTERVALO_SEGUNDOS,
                            help="Segundos entre ciclos (5 por defecto).")
        parser.add_argument("--lote", type=int, default=worker.TAMANO_LOTE,
                            help="Notificaciones por ciclo (20 por defecto).")

    def handle(self, *args, **opciones):
        try:
            obtener_canal = worker.cargar_resolver()
        except ImportError as exc:
            raise CommandError(
                f"No encontré la función de canales ({worker.RESOLVER_CANAL}). "
                "Hace falta la interfaz Canal de t-07/st-35."
            ) from exc

        self.detener = False
        if not opciones["una_vez"]:
            # docker compose stop manda SIGTERM: termina el lote en curso y sale limpio.
            signal.signal(signal.SIGTERM, self._pedir_alto)
            signal.signal(signal.SIGINT, self._pedir_alto)
            logger.info("Worker de notificaciones iniciado (cada %ss, lotes de %s)",
                        opciones["intervalo"], opciones["lote"])

        while True:
            resultado = worker.procesar_lote(opciones["lote"], obtener_canal)
            if resultado.total:
                logger.info("Lote procesado: %s enviadas, %s fallidas, %s pospuestas",
                            resultado.enviadas, resultado.fallidas, resultado.pospuestas)
            if opciones["una_vez"] or self.detener:
                break
            time.sleep(opciones["intervalo"])
            if self.detener:
                break
            close_old_connections()  # si PostgreSQL cerró la conexión durante la espera, abre una nueva

        if opciones["una_vez"]:
            self.stdout.write(
                f"{resultado.enviadas} enviadas, {resultado.fallidas} fallidas, {resultado.pospuestas} pospuestas"
            )

    def _pedir_alto(self, signum, frame):
        logger.info("Señal %s recibida: el worker se detiene al terminar el lote", signum)
        self.detener = True
