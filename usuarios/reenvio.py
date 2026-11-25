import math
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.codigos import generar_codigo
from usuarios.models import CodigoVerificacion, Estado, Proposito, Usuario
from usuarios.telefono import normalizar_telefono


MENSAJE_REENVIO = "Si la cuenta existe y está pendiente, te enviamos un nuevo código."

ESPERA_REENVIO_SEGUNDOS = 60
MAX_REENVIOS_POR_HORA = 3
VENTANA_HORA_SEGUNDOS = 3600


class ReenviarCodigoView(APIView):
    """HU-04 / ST-75-ST-77: POST /api/v1/auth/reenviar-codigo/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["auth"])
    def post(self, request):
        identificador = request.data.get("identificador", "").strip()
        canal = request.data.get("canal")

        if not identificador:
            return Response(
                {"mensaje": MENSAJE_REENVIO},
                status=status.HTTP_200_OK,
            )

        # 1. Buscar al usuario (por correo o teléfono).
        usuario = Usuario.objects.filter(
            email__iexact=identificador
        ).first()

        if usuario is None:
            try:
                telefono = normalizar_telefono(identificador)
                usuario = Usuario.objects.filter(
                    telefono=telefono
                ).first()
            except DjangoValidationError:
                usuario = None

        # 2. Si el usuario existe y está pendiente, procesar el reenvío.
        if usuario and usuario.estado == Estado.PENDIENTE:
            with transaction.atomic():
                # ST-76: Bloquear al usuario para evitar reenvíos simultáneos.
                usuario = Usuario.objects.select_for_update().get(
                    pk=usuario.pk
                )

                if usuario.estado == Estado.PENDIENTE:
                    ahora = timezone.now()

                    # ST-76: Consultar el último código de activación generado.
                    ultimo_codigo = (
                        CodigoVerificacion.objects.filter(
                            usuario=usuario,
                            proposito=Proposito.ACTIVACION,
                        )
                        .order_by("-creado_en", "-id")
                        .first()
                    )

                    # ST-76: Verificar que hayan transcurrido 60 segundos.
                    if ultimo_codigo is not None:
                        tiempo_limite = ultimo_codigo.creado_en + timedelta(
                            seconds=ESPERA_REENVIO_SEGUNDOS
                        )

                        if ahora < tiempo_limite:
                            segundos_restantes = math.ceil(
                                (tiempo_limite - ahora).total_seconds()
                            )

                            return Response(
                                {
                                    "mensaje": (
                                        "Debes esperar antes de solicitar "
                                        "otro código."
                                    )
                                },
                                status=status.HTTP_429_TOO_MANY_REQUESTS,
                                headers={
                                    "Retry-After": str(segundos_restantes)
                                },
                            )

                    # ST-77: Máximo 3 reenvíos por hora por usuario.
                    inicio_ventana = ahora - timedelta(
                        seconds=VENTANA_HORA_SEGUNDOS
                    )
                    codigos_ventana = list(
                        CodigoVerificacion.objects.filter(
                            usuario=usuario,
                            proposito=Proposito.ACTIVACION,
                            creado_en__gte=inicio_ventana,
                        ).order_by("creado_en", "id")
                    )

                    primer_codigo_usuario = (
                        CodigoVerificacion.objects.filter(
                            usuario=usuario,
                            proposito=Proposito.ACTIVACION,
                        )
                        .order_by("creado_en", "id")
                        .first()
                    )

                    reenvios_en_ventana = [
                        c
                        for c in codigos_ventana
                        if primer_codigo_usuario is None
                        or c.pk != primer_codigo_usuario.pk
                    ]

                    if len(reenvios_en_ventana) >= MAX_REENVIOS_POR_HORA:
                        reenvio_mas_antiguo = reenvios_en_ventana[0]
                        fin_bloqueo = reenvio_mas_antiguo.creado_en + timedelta(
                            seconds=VENTANA_HORA_SEGUNDOS
                        )
                        segundos_restantes = max(
                            1,
                            math.ceil((fin_bloqueo - ahora).total_seconds()),
                        )

                        return Response(
                            {
                                "mensaje": (
                                    "Has alcanzado el límite de reenvíos "
                                    "por hora. Intenta más tarde."
                                )
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={"Retry-After": str(segundos_restantes)},
                        )

                    # Invalidar códigos previos de activación.
                    CodigoVerificacion.objects.filter(
                        usuario=usuario,
                        proposito=Proposito.ACTIVACION,
                        usado=False,
                    ).update(usado=True)

                    # Generar el nuevo código y encolarlo.
                    generar_codigo(
                        usuario,
                        Proposito.ACTIVACION,
                        canal,
                    )

        # 3. Respuesta genérica para evitar enumeración de cuentas.
        return Response(
            {"mensaje": MENSAJE_REENVIO},
            status=status.HTTP_200_OK,
        )