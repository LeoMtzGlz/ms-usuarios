"""Rutas de autenticación: se montan en /api/v1/auth/ (config/urls.py)."""
from django.urls import path

from usuarios.views import RegistroView, CustomTokenObtainPairView

app_name = "auth"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"), 
]