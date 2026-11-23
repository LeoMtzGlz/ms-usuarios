"""Filtros del listado de usuarios (HU-16 / ST-145)."""
import django_filters

from comun.roles import Rol
from usuarios.models import Estado, Usuario


class UsuarioFilter(django_filters.FilterSet):
    """`?rol=operativo&estado=activo`. Un valor que no existe responde 400, no una lista vacía."""

    rol = django_filters.ChoiceFilter(choices=Rol.choices)
    estado = django_filters.ChoiceFilter(choices=Estado.choices)

    class Meta:
        model = Usuario
        fields = ["rol", "estado"]
