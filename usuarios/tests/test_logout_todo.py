import pytest
from rest_framework.test import APIClient

from usuarios.tests.factories import UsuarioFactory
from comun.models import EventoAuditoria

@pytest.mark.django_db
class TestLogoutTodo: 
    URL = "/api/v1/auth/logout-todo/"

    def test_sin_token_responde_401(self):
        client = APIClient()
        response = client.post(self.URL)
        assert response.status_code == 401

    def test_cierra_sesion_en_todos_los_dispositivos(self):
        usuario = UsuarioFactory()
        version_antes = usuario.token_version
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(self.URL)

        assert response.status_code == 200
        assert response.data["mensaje"] == "Sesión cerrada en todos los dispositivos."
        usuario.refresh_from_db()
        assert usuario.token_version == version_antes + 1

    def test_registra_el_evento_sin_datos_sensibles(self):
        usuario = UsuarioFactory()
        client = APIClient()
        client.force_authenticate(user=usuario)

        client.post(self.URL)

        assert EventoAuditoria.objects.filter(
            usuario=usuario, accion="logout_todo"
        ).exists()

    def test_segundo_logout_vuelve_a_incrementar(self):
        usuario = UsuarioFactory()
        client = APIClient()
        client.force_authenticate(user=usuario)

        client.post(self.URL)
        client.post(self.URL)

        usuario.refresh_from_db()
        assert usuario.token_version == 2

    def test_solo_incrementa_al_usuario_que_cierra_sesion(self):
        usuario = UsuarioFactory()
        otro = UsuarioFactory()
        version_otro_antes = otro.token_version
        client = APIClient()
        client.force_authenticate(user=usuario)

        client.post(self.URL)

        otro.refresh_from_db()
        assert otro.token_version == version_otro_antes

    def test_solo_acepta_post(self):
        usuario = UsuarioFactory()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.get(self.URL)

        assert response.status_code == 405