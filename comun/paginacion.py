"""Paginación compartida por los listados de la API (HU-16 en adelante)."""
from rest_framework.pagination import PageNumberPagination


class PaginacionDe20(PageNumberPagination):
    """Páginas de 20 en 20: `?page=2`. El cliente no puede cambiar el tamaño.

    Responde {"count", "next", "previous", "results"}. Una página fuera de rango
    responde 404, igual que en el resto de DRF.
    """

    page_size = 20
