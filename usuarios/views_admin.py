"""Administración de usuarios: alta (HU-15 / ST-140) y listado (HU-16 / ST-145)."""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.response import Response

from comun.eventos import registrar_evento
from comun.paginacion import PaginacionDe20
from comun.permisos import EsAdministrador, permisos_por_defecto_mas
from notificaciones.models import CanalNotificacion
from notificaciones.services import notificar
from usuarios.bloqueos import con_bloqueada
from usuarios.contrasenas import generar_contrasena_temporal
from usuarios.filtros import UsuarioFilter
from usuarios.models import Usuario
from usuarios.models import Estado  # t-18/st-153 
from usuarios.serializers_admin import (
    CAMPOS_EDITABLES,
    AltaUsuarioSerializer,
    EdicionUsuarioSerializer,
    UsuarioListaSerializer,
    CambioRolSerializer,
)

PLANTILLA_CUENTA_CREADA = "cuenta_creada"  # notificaciones/plantillas.py

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


class UsuariosView(ListModelMixin, GenericAPIView):
    """/api/v1/usuarios/ · solo administradores.

    GET (HU-16): lista paginada de 20 en 20. `?search=` busca por nombre, apellidos, correo o
    teléfono; `?rol=` y `?estado=` filtran. Ordenada por nombre, apellidos y correo.

    POST (HU-15) {"nombre", "apellidos", "correo", "telefono"}: crea una cuenta operativa, activa
    y con contraseña temporal. Responde 201 con los datos de la cuenta y la contraseña temporal,
    que no se puede volver a consultar.
    """

    # Se conservan IsAuthenticated y ContrasenaDefinitiva de settings y se suma EsAdministrador
    permission_classes = permisos_por_defecto_mas(EsAdministrador)
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = UsuarioFilter
    search_fields = ["first_name", "last_name", "email", "telefono"]
    pagination_class = PaginacionDe20

    def get_queryset(self):
        # El orden fijo es necesario: sin él, las páginas podrían repetir o saltarse usuarios
        return con_bloqueada(Usuario.objects.all()).order_by("first_name", "last_name", "email")

    def get_serializer_class(self):
        if getattr(self.request, "method", None) == "POST":
            return AltaUsuarioSerializer
        return UsuarioListaSerializer

    @extend_schema(responses=UsuarioListaSerializer(many=True), tags=["usuarios"])
    def get(self, request):
        return self.list(request)

    @extend_schema(request=AltaUsuarioSerializer, responses={201: RespuestaAlta}, tags=["usuarios"])
    def post(self, request):
        serializer = AltaUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contrasena = generar_contrasena_temporal()
        with transaction.atomic():
            usuario = serializer.save(contrasena=contrasena)
            # ST-142: el aviso se encola en la misma transacción: si falla, tampoco queda la cuenta.
            # El contexto no lleva la contraseña: la bandeja de salida la guardaría en la base.
            notificar(
                usuario,
                plantilla=PLANTILLA_CUENTA_CREADA,
                contexto={"nombre": usuario.first_name, "correo": usuario.email},
                canal=CanalNotificacion.CORREO,
            )

        # La contraseña no va a la bitácora: solo quién creó a quién y con qué rol.
        registrar_evento("alta_usuario", request.user, request, creado_id=str(usuario.id), rol=usuario.rol)

        respuesta = Response(
            {**serializer.data, "contrasena_temporal": contrasena}, status=status.HTTP_201_CREATED
        )
        respuesta["Cache-Control"] = "no-store"  # la contraseña no debe quedar en cachés
        return respuesta


# t-17/st-149: edición de un usuario (HU-17)
class UsuarioDetalleView(UpdateModelMixin, GenericAPIView):
    """/api/v1/usuarios/{id}/ · solo administradores.

    PATCH (HU-17) {"nombre", "apellidos", "correo", "telefono"}: edita los datos de contacto.
    Cualquier otro campo responde 400. Solo acepta PATCH: los demás métodos responden 405.
    """

    permission_classes = permisos_por_defecto_mas(EsAdministrador)
    queryset = Usuario.objects.all()
    serializer_class = EdicionUsuarioSerializer

    @extend_schema(
        summary="Editar datos de un usuario (solo admin)",
        request=EdicionUsuarioSerializer,
        responses={
            200: EdicionUsuarioSerializer,
            400: OpenApiResponse(description="Duplicado o campo no editable"),
            401: OpenApiResponse(description="Sin token"),
            403: OpenApiResponse(description="No es administrador"),
            404: OpenApiResponse(description="Usuario no existe"),
        },
        tags=["usuarios"],
    )
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    # t-17/st-150: registra en la bitácora qué campos cambiaron y quién lo hizo
    def perform_update(self, serializer):
        usuario = serializer.instance
        fuentes = {campo: serializer.fields[campo].source for campo in CAMPOS_EDITABLES}
        antes = {campo: getattr(usuario, fuente) for campo, fuente in fuentes.items()}

        usuario = serializer.save()

        cambiados = [campo for campo, fuente in fuentes.items() if getattr(usuario, fuente) != antes[campo]]
        if cambiados:
            # Solo los nombres de los campos: correo y teléfono son datos personales.
            registrar_evento(
                "usuario_editado",
                self.request.user,
                self.request,
                editado_id=str(usuario.pk),
                campos_cambiados=cambiados,
            )
            

# t-18/st-153: desactivar y reactivar una cuenta (HU-18)
RespuestaEstado = inline_serializer(
    name="EstadoUsuarioRespuesta",
    fields={"id": serializers.UUIDField(), "estado": serializers.CharField()},
)
RESPUESTAS_ESTADO = {
    200: RespuestaEstado,
    400: OpenApiResponse(description="Acción no permitida para esta cuenta"),
    401: OpenApiResponse(description="Sin token"),
    403: OpenApiResponse(description="No es administrador"),
    404: OpenApiResponse(description="Usuario no existe"),
}


class _CambioDeEstadoView(GenericAPIView):
    """Base de /desactivar/ y /reactivar/: solo administradores, 404 si el usuario no existe.

    El cambio lo hace Usuario.cambiar_estado(), que también actualiza is_active,
    incrementa token_version al desactivar (cierra todas las sesiones) y registra
    el evento estado_cambiado con el administrador que lo hizo. Nunca se borra el registro.
    """

    permission_classes = permisos_por_defecto_mas(EsAdministrador)
    queryset = Usuario.objects.all()

    @staticmethod
    def respuesta(usuario):
        return Response({"id": str(usuario.pk), "estado": usuario.estado})


class DesactivarUsuarioView(_CambioDeEstadoView):
    """POST /api/v1/usuarios/{id}/desactivar/ · HU-18."""

    @extend_schema(
        summary="Desactivar una cuenta (solo admin)", request=None, responses=RESPUESTAS_ESTADO, tags=["usuarios"]
    )
    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            raise serializers.ValidationError("No puedes desactivar tu propia cuenta.")
        if usuario.estado != Estado.INACTIVO:  # si ya está inactiva no se repite el cambio
            usuario.cambiar_estado(Estado.INACTIVO, por=request.user)
        return self.respuesta(usuario)


class ReactivarUsuarioView(_CambioDeEstadoView):
    """POST /api/v1/usuarios/{id}/reactivar/ · HU-18."""

    @extend_schema(
        summary="Reactivar una cuenta (solo admin)", request=None, responses=RESPUESTAS_ESTADO, tags=["usuarios"]
    )
    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.estado == Estado.PENDIENTE:
            raise serializers.ValidationError(
                "Una cuenta pendiente se activa con su código de verificación, no se reactiva."
            )
        if usuario.estado == Estado.INACTIVO:  # si ya está activa no se repite el cambio
            usuario.cambiar_estado(Estado.ACTIVO, por=request.user)
        return self.respuesta(usuario)

# t-14/st-131: cambio de rol de un usuario (HU-14)
RespuestaRol = inline_serializer(
    name="RolUsuarioRespuesta",
    fields={"id": serializers.UUIDField(), "rol": serializers.CharField()},
)


class CambiarRolView(GenericAPIView):
    """PATCH /api/v1/usuarios/{id}/rol/ · solo administradores (HU-14 / ST-131).

    Asigna un rol válido al usuario objetivo. Un administrador no puede
    cambiarse ni quitarse su propio rol.
    """

    permission_classes = permisos_por_defecto_mas(EsAdministrador)
    queryset = Usuario.objects.all()
    serializer_class = CambioRolSerializer

    @extend_schema(
        summary="Cambiar el rol de un usuario (solo admin)",
        request=CambioRolSerializer,
        responses={
            200: RespuestaRol,
            400: OpenApiResponse(description="Rol inválido o intento de cambiar el propio rol"),
            401: OpenApiResponse(description="Sin token"),
            403: OpenApiResponse(description="No es administrador"),
            404: OpenApiResponse(description="Usuario no existe"),
        },
        tags=["usuarios"],
    )
    def patch(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            raise serializers.ValidationError("No puedes cambiar tu propio rol.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nuevo_rol = serializer.validated_data["rol"]
        if usuario.rol != nuevo_rol:
            usuario.rol = nuevo_rol
            usuario.save(update_fields=["rol"])

        return Response(
            {"id": str(usuario.pk), "rol": usuario.rol},
            status=status.HTTP_200_OK,
        )