# t-22/st-168
"""HU-22 / ST-168: GET /api/v1/auth/accesos/ · historial de accesos de la persona que pregunta.

- Solo devuelve los registros del usuario del token (nunca recibe el usuario por parámetro).
- Los últimos 20 por página, del más reciente al más antiguo; el cliente no puede pedir más.
- No expone el user-agent crudo ni el id del usuario.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from usuarios.models import RegistroAcceso

ACCESOS_POR_PAGINA = 20


class RegistroAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcceso
        fields = ["fecha", "ip", "dispositivo", "exitoso"]
        read_only_fields = fields


class PaginacionAccesos(PageNumberPagination):
    page_size = ACCESOS_POR_PAGINA
    page_size_query_param = None  # ?page_size=1000 se ignora
    max_page_size = ACCESOS_POR_PAGINA


class HistorialAccesosView(ListAPIView):
    """Últimos accesos (exitosos y fallidos) de mi cuenta, con dispositivo legible.

    Usa los permisos por defecto: sin token responde 401 y con contraseña
    temporal responde 403 debe_cambiar_password (ST-116).
    """

    serializer_class = RegistroAccesoSerializer
    pagination_class = PaginacionAccesos

    def get_queryset(self):
        return RegistroAcceso.objects.filter(usuario=self.request.user).order_by("-fecha", "-id")

    @extend_schema(tags=["auth"], summary="Ver mi historial de accesos")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)