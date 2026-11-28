"""t-33/st-219 (HU-33): POST /api/v1/auth/google/"""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.login_google import obtener_o_crear_usuario, verificar_id_token
from usuarios.tokens import completar_login


class LoginGoogleSerializer(serializers.Serializer):
    id_token = serializers.CharField(trim_whitespace=True)
    recordarme = serializers.BooleanField(required=False, default=False)  # igual que el login (HU-06)
    acepto_privacidad = serializers.BooleanField(required=False, default=False)  # solo si se crea la cuenta


class LoginGoogleView(APIView):
    """Inicia sesión (o crea la cuenta) con el ID token que el frontend obtuvo de Google.

    Responde lo mismo que POST /api/v1/auth/login/: los JWT, o el token temporal si la
    cuenta tiene 2FA activo. Agrega "cuenta_nueva" para que el frontend sepa si acaba de
    crearse (por ejemplo, para pedir el teléfono o mostrar el aviso de privacidad).
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # público: un token viejo no debe dar 401
    throttle_scope = "login"  # mismo límite que el login con contraseña (t-24/st-179)

    def get_authenticate_header(self, request):
        # Sin clases de autenticación DRF convierte los 401 en 403; así responde 401 como el login
        return 'Bearer realm="api"'

    @extend_schema(
        request=LoginGoogleSerializer,
        responses={
            200: OpenApiResponse(description="JWT (o token temporal si tiene 2FA) y cuenta_nueva"),
            400: OpenApiResponse(description="datos_invalidos: falta id_token"),
            401: OpenApiResponse(description="token_google_invalido"),
            403: OpenApiResponse(description="cuenta_inactiva"),
            503: OpenApiResponse(description="google_no_configurado"),
        },
        tags=["auth"],
        summary="Iniciar sesión con Google",
    )
    def post(self, request):
        serializer = LoginGoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        info = verificar_id_token(datos["id_token"])
        usuario, creado = obtener_o_crear_usuario(info, request, acepto_privacidad=datos["acepto_privacidad"])

        respuesta = completar_login(usuario, request, datos["recordarme"])
        respuesta["cuenta_nueva"] = creado
        return Response(respuesta)