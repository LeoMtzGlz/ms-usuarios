import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.urls import reverse
from usuarios.models import RegistroAcceso, Usuario, Estado


@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_notifica_dispositivo_nuevo(mock_notificar, api_client, llaves): # <--- Agregamos 'llaves' aquí
    """t-28/st-198: Verifica que se encola una notificación al entrar desde un dispositivo nuevo."""
    
    # 1. Creamos un usuario ACTIVO
    user = Usuario.objects.create_user(
        email="test_dev@example.com",
        password="Password123!",
        first_name="Test",
        last_name="Device",
        estado=Estado.ACTIVO
    )
    
    # 2. Creamos un registro de acceso viejo (hace 100 días) 
    RegistroAcceso.objects.create(
        usuario=user,
        dispositivo="Chrome en Windows",
        exitoso=True,
        fecha=timezone.now() - timedelta(days=100)
    )
    
    # 3. Hacemos login desde un dispositivo nuevo (Firefox)
    url = reverse('auth:login')
    response = api_client.post(
        url, 
        {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
    )
    
    # 4. Verificamos que el login fue exitoso y que se encoló la notificación
    assert response.status_code == 200
    mock_notificar.assert_called_once()
    assert mock_notificar.call_args.kwargs['plantilla'] == 'dispositivo_nuevo'