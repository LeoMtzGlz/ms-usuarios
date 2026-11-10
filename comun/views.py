
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class SaludView(APIView):
    """GET /api/v1/salud/: confirma que la API vive y que PostgreSQL responde."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except OperationalError:
            return Response({"estado": "error", "bd": "error"}, status=503)
        return Response({"estado": "ok", "bd": "ok"})

