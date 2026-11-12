from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.errores import CodigoInvalido, CuentaInactiva
from comun.eventos import registrar_evento
from usuarios.codigos import verificar_codigo
from usuarios.models import Canal, Estado, Proposito, Usuario
from usuarios.serializers import ActivarSerializer
from usuarios.telefono import normalizar_telefono


def buscar_usuario(identificador: str):
    """Busca por correo o por teléfono. Devuelve None si no existe."""
    identificador = identificador.strip()
    if "@" in identificador:
        return Usuario.objects.filter(email=identificador.lower()).first()
    try:
        telefono = normalizar_telefono(identificador)
    except ValidationError:
        return None
    return Usuario.objects.filter(telefono=telefono).first()


class ActivarCuentaView(APIView):
    """POST /api/v1/auth/activar/  {identificador, codigo}"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        datos = ActivarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        usuario = buscar_usuario(datos.validated_data["identificador"])
        if usuario is None:
            # Mismo error que un código malo: no revelamos qué cuentas existen
            raise CodigoInvalido()

        codigo = verificar_codigo(usuario, Proposito.ACTIVACION, datos.validated_data["codigo"])

        if usuario.estado == Estado.INACTIVO:
            raise CuentaInactiva()

        if codigo.canal == Canal.CORREO:
            usuario.email_verificado = True
            campo = "email_verificado"
        else:
            usuario.telefono_verificado = True
            campo = "telefono_verificado"
        usuario.save(update_fields=[campo])

        if usuario.estado == Estado.PENDIENTE:
            usuario.cambiar_estado(Estado.ACTIVO)  # ya registra el evento estado_cambiado

        registrar_evento("cuenta_activada", usuario, request=request, canal=codigo.canal)
        return Response({"estado": usuario.estado, "mensaje": "Tu cuenta quedó activa."})