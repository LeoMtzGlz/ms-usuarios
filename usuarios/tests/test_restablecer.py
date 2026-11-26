import pytest
from django.contrib.auth import get_user_model
from usuarios.models import Estado, Proposito
from usuarios.codigos import crear_codigo
from usuarios.tests.factories import UsuarioFactory
from notificaciones.models import Notificacion

Usuario = get_user_model()
URL = "/api/v1/auth/restablecer/"

@pytest.mark.django_db
def test_restablecer_exitoso(api_client):
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    _, codigo = crear_codigo(usuario, Proposito.RECUPERACION)

    response = api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": codigo,
        "password": "NuevaPassword123",
        "password_confirmacion": "NuevaPassword123"
    })

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password("NuevaPassword123")
    assert usuario.token_version > 0

# t-10/st-109
@pytest.mark.django_db
def test_restablecer_encola_notificacion(api_client):
    """ST-109: Verifica que se cree la notificación de aviso."""
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    _, codigo = crear_codigo(usuario, Proposito.RECUPERACION)

    api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": codigo,
        "password": "NuevaPassword123",
        "password_confirmacion": "NuevaPassword123"
    })

    assert Notificacion.objects.filter(destinatario=usuario, plantilla="password_cambiada").exists()