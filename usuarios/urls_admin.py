"""Rutas de administración de usuarios: se montan en /api/v1/usuarios/ (config/urls.py)."""
from django.urls import path

from usuarios.views_admin import UsuarioDetalleView, UsuariosView
from usuarios.views_admin import DesactivarUsuarioView, ReactivarUsuarioView  # t-18/st-153

app_name = "usuarios"

urlpatterns = [
    path("", UsuariosView.as_view(), name="usuarios"),  # hu-15/st-140 (POST) y hu-16/st-145 (GET)
    path("<uuid:pk>/", UsuarioDetalleView.as_view(), name="usuario-detalle"),  # t-17/st-149 (PATCH)
    path("<uuid:pk>/desactivar/", DesactivarUsuarioView.as_view(), name="usuario-desactivar"),  # t-18/st-153
    path("<uuid:pk>/reactivar/", ReactivarUsuarioView.as_view(), name="usuario-reactivar"),  # t-18/st-153
]