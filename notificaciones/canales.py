import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("svc.notificaciones")


class Canal(ABC):
    """Clase base para todos los canales de notificación."""

    @abstractmethod
    def enviar(self, destino: str, asunto: str, texto: str) -> None:
        """Envía el mensaje al destino indicado."""
        pass


class CanalConsola(Canal):
    """Canal para desarrollo: imprime el mensaje en la consola."""

    def enviar(self, destino: str, asunto: str, texto: str) -> None:
        logger.info("--- MENSAJE A CONSOLA ---")
        logger.info("Para: %s", destino)
        logger.info("Asunto: %s", asunto)
        logger.info("Mensaje: %s", texto)
        logger.info("-------------------------")