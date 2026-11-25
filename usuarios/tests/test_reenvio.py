import pytest
from usuarios.models import Estado, CodigoVerificacion, Proposito
from usuarios.tests.factories import UsuarioFactory

URL = "/api/v1/auth/reenviar-codigo/"


@pytest.mark.django_db
def test_reenvio_genera_nuevo_codigo_e_invalida_el_anterior(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    # Creamos un código viejo
    codigo_viejo = CodigoVerificacion.objects.create(
        usuario=usuario, proposito=Proposito.ACTIVACION, canal="correo",
        codigo_hash="hash_falso", expira_en="2026-01-01T00:00:00Z", usado=False
    )

    response = api_client.post(URL, {"identificador": usuario.email})

    assert response.status_code == 200
    assert "mensaje" in response.data

    codigo_viejo.refresh_from_db()
    assert codigo_viejo.usado is True
    assert CodigoVerificacion.objects.filter(usuario=usuario, usado=False).count() == 1


@pytest.mark.django_db
def test_reenvio_respuesta_generica_usuario_inexistente(api_client):
    response = api_client.post(URL, {"identificador": "noexiste@ejemplo.com"})
    assert response.status_code == 200
    assert "mensaje" in response.data


@pytest.mark.django_db
def test_reenvio_no_hace_nada_si_usuario_esta_activo(api_client):
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    response = api_client.post(URL, {"identificador": usuario.email})

    assert response.status_code == 200
    assert not CodigoVerificacion.objects.filter(usuario=usuario).exists()