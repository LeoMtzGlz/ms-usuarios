"""HU-15 / ST-140: alta de usuarios operativos por un administrador."""
from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from comun.eventos import registrar_evento
from comun.permisos import EsAdministrador, permisos_por_defecto_mas
from usuarios.contrasenas import generar_contrasena_temporal
from usuarios.serializers_admin import AltaUsuarioSerializer

RespuestaAlta = inline_serializer(
    name="AltaUsuarioRespuesta",
    fields={
        "id": serializers.UUIDField(),
        "nombre": serializers.CharField(),
        "apellidos": serializers.CharField(),
        "correo": serializers.EmailField(),
        "telefono": serializers.CharField(),
        "rol": serializers.CharField(),
        "estado": serializers.CharField(),
        "debe_cambiar_password": serializers.BooleanField(),
        "zona": serializers.DictField(),
        "contrasena_temporal": serializers.CharField(help_text="Se devuelve una sola vez."),
    },
)


class AltaUsuarioView(APIView):
    """POST /api/v1/usuarios/  {"nombre", "apellidos", "correo", "telefono"}

    Crea una cuenta operativa, activa y con contraseña temporal. Responde 201 con los
    datos de la cuenta y la contraseña temporal, que no se puede volver a consultar.
    """

    # Se conservan IsAuthenticated y ContrasenaDefinitiva de settings y se suma EsAdministrador
    permission_classes = permisos_por_defecto_mas(EsAdministrador)

    @extend_schema(request=AltaUsuarioSerializer, responses={201: RespuestaAlta}, tags=["usuarios"])
    def post(self, request):
        serializer = AltaUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contrasena = generar_contrasena_temporal()
        with transaction.atomic():
            usuario = serializer.save(contrasena=contrasena)
            # ST-142: aquí se encolará el aviso de cuenta creada (sin la contraseña).

        # La contraseña no va a la bitácora: solo quién creó a quién y con qué rol.
        registrar_evento("alta_usuario", request.user, request, creado_id=str(usuario.id), rol=usuario.rol)

        respuesta = Response(
            {**serializer.data, "contrasena_temporal": contrasena}, status=status.HTTP_201_CREATED
        )
        respuesta["Cache-Control"] = "no-store"  # la contraseña no debe quedar en cachés
        return respuesta
