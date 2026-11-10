"""Vistas de prueba que provocan cada tipo de error."""
from django.urls import path
from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.errores import CodigoExpirado, CredencialesInvalidas, CuentaPendiente


class Datos(serializers.Serializer):
    correo = serializers.EmailField()
    edad = serializers.IntegerField(min_value=0)


class Validacion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        Datos(data=request.data).is_valid(raise_exception=True)
        return Response({})


class SinCredenciales(BaseAuthentication):
    """No autentica a nadie, pero declara el esquema Bearer.

    DRF solo responde 401 si la primera clase de autenticación de la vista define
    authenticate_header(); si no, convierte el 401 en 403. Desde T-04 esa clase es la de JWT.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return "Bearer"


class Lanza(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SinCredenciales]
    errores = {
        "credenciales": CredencialesInvalidas,
        "pendiente": CuentaPendiente,
        "codigo": CodigoExpirado,
    }

    def get(self, request, cual):
        if cual == "throttle":
            raise Throttled(wait=42)
        if cual == "explota":
            raise RuntimeError("detalle interno que nunca debe verse")
        raise self.errores[cual]()


urlpatterns = [
    path("validacion/", Validacion.as_view()),
    path("lanza/<str:cual>/", Lanza.as_view()),
]
