"""t-13/st-123: Pruebas de DEFAULT_PERMISSION_CLASSES (T-13, criterio 3).

Por defecto todo endpoint exige autenticación; los públicos declaran AllowAny.
"""

import pytest
from django.conf import settings
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

pytestmark = pytest.mark.django_db


class _VistaSinPermisos(APIView):
    """Vista que no declara permission_classes: hereda los de settings."""

    def get(self, request):
        return Response({"ok": True})


def test_settings_exige_autenticacion_por_defecto():
    clases = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    assert "rest_framework.permissions.IsAuthenticated" in clases


def test_vista_sin_permisos_declarados_responde_401_sin_token():
    respuesta = _VistaSinPermisos.as_view()(APIRequestFactory().get("/x/"))
    assert respuesta.status_code == 401
    assert respuesta.data["codigo"] == "no_autenticado"


def test_salud_sigue_siendo_publica():
    assert APIClient().get("/api/v1/salud/").status_code == 200


def test_registro_sigue_siendo_publico():
    """Sin datos responde 400 (validación), no 401: el endpoint es público."""
    assert APIClient().post("/api/v1/auth/registro/", {}, format="json").status_code == 400


@pytest.mark.parametrize("ruta", ["/api/schema/", "/api/docs/"])
def test_documentacion_de_la_api_sigue_siendo_publica(ruta):
    assert APIClient().get(ruta).status_code == 200
