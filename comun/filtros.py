"""Filtros de la bitácora (HU-26 / ST-189)."""
import django_filters

from comun.models import EventoAuditoria


class EventoAuditoriaFilter(django_filters.FilterSet):
    """`?accion=login&usuario=<uuid>&desde=2026-11-01&hasta=2026-11-30`. Un valor mal formado responde 400."""

    usuario = django_filters.UUIDFilter(field_name="usuario_id")
    # shortcut: el filtro por fecha usa fecha__date y no aprovecha el índice auditoria_fecha_idx;
    # pasar a rangos de datetime si la tabla crece mucho
    desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")

    class Meta:
        model = EventoAuditoria
        fields = ["accion", "usuario", "desde", "hasta"]
