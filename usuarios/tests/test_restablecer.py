import pytest
from django.contrib.auth import get_user_model
from usuarios.models import Estado, Proposito
from usuarios.codigos import crear_codigo
from usuarios.tests.factories import UsuarioFactory
from notificaciones.models import Notificacion
from django.utils import timezone
from usuarios.models import CodigoVerificacion

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

# t-10/st-110
@pytest.mark.django_db
def test_restablecer_codigo_incorrecto(api_client):
    """ST-110: Verifica que un código malo no cambie la contraseña."""
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    crear_codigo(usuario, Proposito.RECUPERACION)

    response = api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": "000000",
        "password": "NuevaPassword123",
        "password_confirmacion": "NuevaPassword123"
    })

    assert response.status_code == 400
    usuario.refresh_from_db()
    assert not usuario.check_password("NuevaPassword123")


@pytest.mark.django_db
def test_restablecer_codigo_vencido(api_client):
    """ST-110: Verifica que un código vencido sea rechazado."""
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    _, codigo = crear_codigo(usuario, Proposito.RECUPERACION)

    registro = CodigoVerificacion.objects.get(usuario=usuario, usado=False)
    registro.expira_en = timezone.now() - timezone.timedelta(minutes=1)
    registro.save(update_fields=["expira_en"])

    response = api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": codigo,
        "password": "NuevaPassword123",
        "password_confirmacion": "NuevaPassword123"
    })

    assert response.status_code == 400


@pytest.mark.django_db
def test_restablecer_passwords_no_coinciden(api_client):
    """ST-110: Verifica que las contraseñas deben coincidir."""
    usuario = UsuarioFactory(estado=Estado.ACTIVO)
    _, codigo = crear_codigo(usuario, Proposito.RECUPERACION)

    response = api_client.post(URL, {
        "identificador": usuario.email,
        "codigo": codigo,
        "password": "NuevaPassword123",
        "password_confirmacion": "OtraPasswordDiferente123"
    })

    assert response.status_code == 400