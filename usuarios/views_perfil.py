"""Endpoint del perfil del usuario autenticado (HU-21 / ST-163)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from usuarios.serializers_perfil import PerfilSerializer


class PerfilView(GenericAPIView):
    """Consulta y edita exclusivamente el perfil de la sesión actual.

    La URL no recibe un identificador. El objeto siempre se obtiene de
    ``request.user``, por lo que una persona no puede pedir el perfil de otra.
    Los permisos globales exigen autenticación y contraseña definitiva.
    """

    serializer_class = PerfilSerializer

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Consultar mi perfil",
        responses={
            200: PerfilSerializer,
            401: OpenApiResponse(description="Sin token o token inválido"),
            403: OpenApiResponse(description="La contraseña temporal todavía no se ha cambiado"),
        },
        tags=["perfil"],
    )
    def get(self, request):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(
        summary="Editar mi perfil",
        request=PerfilSerializer,
        responses={
            200: PerfilSerializer,
            400: OpenApiResponse(description="Campo no editable o valor inválido"),
            401: OpenApiResponse(description="Sin token o token inválido"),
            403: OpenApiResponse(description="La contraseña temporal todavía no se ha cambiado"),
        },
        tags=["perfil"],
    )
    def patch(self, request):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
