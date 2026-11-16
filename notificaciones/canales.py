from abc import ABC, abstractmethod


class Canal(ABC):
    """Clase base para todos los canales de notificación."""

    @abstractmethod
    def enviar(self, destino: str, asunto: str, texto: str) -> None:
        """Envía el mensaje al destino indicado."""
        pass