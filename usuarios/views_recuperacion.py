"""HU-10 / ST-107: vista de solicitud de recuperación de contraseña."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.eventos import registrar_evento
from usuarios.recuperacion import MENSAJE_RECUPERACION, solicitar_recuperacion
from usuarios.serializers import SolicitudRecuperacionSerializer


class SolicitarRecuperacionView(APIView):
    """POST /api/v1/auth/recuperar/

    Recibe correo o teléfono (`identificador`) y, opcionalmente, el `canal`. Siempre responde 200
    con el mismo mensaje, exista o no la cuenta. El código vale 10 minutos y 5 intentos.
    """
    # t-24/st-179: limitar a 3 solicitudes por hora por IP
    throttle_scope = "recuperar"
    
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=SolicitudRecuperacionSerializer, tags=["auth"])
    def post(self, request):
        serializer = SolicitudRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        usuario = solicitar_recuperacion(datos["identificador"], datos.get("canal"))
        if usuario is not None:
            registrar_evento("recuperacion_solicitada", usuario, request)
        return Response({"mensaje": MENSAJE_RECUPERACION}, status=status.HTTP_200_OK)