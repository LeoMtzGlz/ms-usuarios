"""Rutas de administración de usuarios: se montan en /api/v1/usuarios/ (config/urls.py)."""
from django.urls import path

from usuarios.views_admin import AltaUsuarioView

app_name = "usuarios"

urlpatterns = [
    path("", AltaUsuarioView.as_view(), name="alta"),  # hu-15/st-140 (HU-16 agrega GET aquí)
]
