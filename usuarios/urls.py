"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import RegistroView

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
]