
from datetime import timedelta  # ST-76: Calcular el tiempo de espera.

from django.db import transaction
from django.utils import timezone  # ST-76: Consultar la hora actual.
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

ESPERA_REENVIO_SEGUNDOS = 60  # ST-76: Tiempo mínimo entre reenvíos.


class ReenviarCodigoView(APIView):
    """HU-04 / ST-75-ST-76: POST /api/v1/auth/reenviar-codigo/"""
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
                # ST-76: Bloquear al usuario para evitar reenvíos simultáneos.
                usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)

                if usuario.estado == Estado.PENDIENTE:
                    # ST-76: Consultar el último código de activación generado.
                    ultimo_codigo = CodigoVerificacion.objects.filter(
                        usuario=usuario,
                        proposito=Proposito.ACTIVACION,
                    ).order_by("-creado_en").first()

                    # ST-76: Verificar que hayan transcurrido al menos 60 segundos.
                    puede_reenviar = (
                        ultimo_codigo is None
                        or timezone.now() >= (
                            ultimo_codigo.creado_en
                            + timedelta(seconds=ESPERA_REENVIO_SEGUNDOS)
                        )
                    )

                    if puede_reenviar:
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
