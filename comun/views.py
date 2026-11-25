
from django.db import connection
from django.db.utils import OperationalError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.filtros import EventoAuditoriaFilter
from comun.models import EventoAuditoria
from comun.paginacion import PaginacionDe20
from comun.permisos import EsAdministrador, permisos_por_defecto_mas
from comun.serializers import EventoAuditoriaSerializer


class SaludView(APIView):
    """GET /api/v1/salud/: confirma que la API vive y que PostgreSQL responde."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except OperationalError:
            return Response({"estado": "error", "bd": "error"}, status=503)
        return Response({"estado": "ok", "bd": "ok"})


@extend_schema(tags=["auditoria"])
class AuditoriaView(ListAPIView):
    """GET /api/v1/auditoria/ (HU-26): bitácora paginada de 20 en 20, solo administradores, solo lectura."""

    permission_classes = permisos_por_defecto_mas(EsAdministrador)
    http_method_names = ["get", "head", "options"]
    serializer_class = EventoAuditoriaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventoAuditoriaFilter
    pagination_class = PaginacionDe20
    # `-id` desempata las fechas iguales: sin él las páginas podrían repetir o saltarse eventos
    queryset = EventoAuditoria.objects.order_by("-fecha", "-id")
