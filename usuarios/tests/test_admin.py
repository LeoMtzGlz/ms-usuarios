import pytest

from .factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_admin_lista_busca_y_abre_formularios(admin_client):
    usuario = UsuarioFactory(email="buscar@ejemplo.com")
    assert admin_client.get("/admin/usuarios/usuario/?q=buscar").status_code == 200
    assert admin_client.get("/admin/usuarios/usuario/add/").status_code == 200
    assert admin_client.get(f"/admin/usuarios/usuario/{usuario.pk}/change/").status_code == 200
