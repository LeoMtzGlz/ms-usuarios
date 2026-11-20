"""Vistas de la app usuarios."""
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.eventos import registrar_evento
from usuarios.codigos import generar_codigo
from usuarios.models import Proposito
from usuarios.serializers import RegistroSerializer


class RegistroView(APIView):
    """HU-02 / ST-66: POST /api/v1/auth/registro/

    Crea la cuenta (pendiente, rol cliente) y encola el código de activación.
    Todo ocurre en una sola transacción: si falla el código o la notificación,
    la cuenta tampoco se crea. Responde 201 sin tokens: la sesión se inicia
    hasta que la cuenta se active (HU-03).
    """

    # t-24/st-179: Limitar el registro a 5 solicitudes por hora por IP
    throttle_scope = "registro"

    permission_classes = [AllowAny]
    authentication_classes = []  # registro público: un token viejo o inválido no debe dar 401

    @extend_schema(request=RegistroSerializer, responses={201: RegistroSerializer}, tags=["auth"])
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            usuario = serializer.save()  # Usuario.objects.create_user(...)
            generar_codigo(usuario, Proposito.ACTIVACION)

        registrar_evento("registro", usuario, request, canal=usuario.canal_preferido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
