import logging
from abc import ABC, abstractmethod

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

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

# T-08/ST-41: Crear la clase CanalCorreo para enviar notificaciones por correo electrónico
class CanalCorreo(Canal):
    """Canal para enviar notificaciones por correo electrónico."""

    def enviar(self, destino: str, asunto: str, texto: str) -> None:
        mensaje = EmailMultiAlternatives(
            subject=asunto,
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino],
        )

        mensaje.send(fail_silently=False)

        logger.info("Correo enviado correctamente a: %s", destino)