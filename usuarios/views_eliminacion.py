"""HU-23 / ST-174: vista para eliminar la propia cuenta."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.eliminacion import eliminar_cuenta
from usuarios.serializers import EliminarCuentaSerializer

MENSAJE_CUENTA_ELIMINADA = "Tu cuenta fue eliminada."


class EliminarCuentaView(APIView):
    """POST /api/v1/auth/eliminar-cuenta/

    Pide la contraseña actual y la palabra ELIMINAR. Envía un correo de confirmación,
    anonimiza la cuenta (queda inactiva) y cierra todas las sesiones. Es irreversible.
    El único administrador activo no puede eliminarse (403 unico_administrador).
    """

    @extend_schema(request=EliminarCuentaSerializer, tags=["auth"])
    def post(self, request):
        serializer = EliminarCuentaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        eliminar_cuenta(request.user, request=request)
        return Response({"mensaje": MENSAJE_CUENTA_ELIMINADA}, status=status.HTTP_200_OK)