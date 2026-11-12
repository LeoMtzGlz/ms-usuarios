from django.urls import path

from usuarios.views import ActivarCuentaView

urlpatterns = [
    path("activar/", ActivarCuentaView.as_view(), name="activar"),
]