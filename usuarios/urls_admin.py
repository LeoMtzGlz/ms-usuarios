
"""Rutas de administración de usuarios:
se montan en /api/v1/usuarios/ (config/urls.py).
"""

from django.urls import path

from usuarios.views_admin import UsuariosView

app_name = "usuarios"

urlpatterns = [
    # Colección: listado y alta de usuarios.
    path("", UsuariosView.as_view(), name="usuarios"),

    # Detalle: actualización parcial de un usuario.
    path("<uuid:pk>/", UsuariosView.as_view(), name="usuario-detalle"),
]
