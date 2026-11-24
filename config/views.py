"""Vistas propias del proyecto para la documentación de la API."""

from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.renderers import JSONRenderer


class SwaggerView(SpectacularSwaggerView):
    """Renderiza en JSON los errores ocurridos antes de mostrar Swagger.

    La interfaz usa un renderer HTML. Si la autenticación rechaza un JWT, intentar
    renderizar ese error con la plantilla vuelve a evaluar ``request.user`` y
    relanza la excepción. Forzar JSON para las respuestas de error conserva el
    contrato estándar de la API (por ejemplo, ``401 token_invalido``).
    """

    def get(self, request, *args, **kwargs):
        # Swagger no consulta al usuario hasta renderizar la plantilla. Evaluarlo
        # aquí permite que DRF procese un JWT inválido con su exception handler.
        _ = request.user
        return super().get(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, "exception", False):
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = "application/json"
            response.renderer_context = self.get_renderer_context()
        return response
