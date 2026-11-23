"""Rutas de administración de usuarios: se montan en /api/v1/usuarios/ (config/urls.py)."""
from django.urls import path

from usuarios.views_admin import UsuarioDetalleView, UsuariosView

app_name = "usuarios"

urlpatterns = [
    path("", UsuariosView.as_view(), name="usuarios"),  # hu-15/st-140 (POST) y hu-16/st-145 (GET)
    path("<uuid:pk>/", UsuarioDetalleView.as_view(), name="usuario-detalle"),  # t-17/st-149 (PATCH)
]