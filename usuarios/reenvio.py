from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.core.exceptions import ValidationError as DjangoValidationError

from usuarios.models import Usuario, Estado, Proposito, CodigoVerificacion
from usuarios.codigos import generar_codigo
from usuarios.telefono import normalizar_telefono

MENSAJE_REENVIO = "Si la cuenta existe y está pendiente, te enviamos un nuevo código."


class ReenviarCodigoView(APIView):
    """HU-04 / ST-75: POST /api/v1/auth/reenviar-codigo/"""
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["auth"])
    def post(self, request):
        identificador = request.data.get("identificador", "").strip()
        canal = request.data.get("canal")

        if not identificador:
            return Response({"mensaje": MENSAJE_REENVIO}, status=status.HTTP_200_OK)

        # 1. Buscar al usuario (por correo o teléfono)
        usuario = Usuario.objects.filter(email__iexact=identificador).first()

        if usuario is None:
            try:
                telefono = normalizar_telefono(identificador)
                usuario = Usuario.objects.filter(telefono=telefono).first()
            except DjangoValidationError:
                usuario = None

        # 2. Si el usuario existe y está pendiente, generamos un nuevo código
        if usuario and usuario.estado == Estado.PENDIENTE:
            with transaction.atomic():
                # Invalidar códigos previos de activación
                CodigoVerificacion.objects.filter(
                    usuario=usuario,
                    proposito=Proposito.ACTIVACION,
                    usado=False
                ).update(usado=True)

                # Generar el nuevo código y encolarlo
                generar_codigo(usuario, Proposito.ACTIVACION, canal)

        # 3. Respuesta genérica (Nunca revelamos si existe o no)
        return Response({"mensaje": MENSAJE_REENVIO}, status=status.HTTP_200_OK)