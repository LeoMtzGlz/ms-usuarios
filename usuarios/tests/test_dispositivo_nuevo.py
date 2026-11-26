import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.urls import reverse
from usuarios.models import RegistroAcceso, Usuario, Estado
from usuarios.accesos import dispositivo_legible

# User-Agents para las pruebas
UA_FIREFOX_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
UA_CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)
UA_CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)

# Generamos los strings de dispositivo que usará la lógica
DISPOSITIVO_FIREFOX_MAC = dispositivo_legible(UA_FIREFOX_MAC)
DISPOSITIVO_CHROME_WINDOWS = dispositivo_legible(UA_CHROME_WINDOWS)

@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_dispositivo_nuevo_notifica(mock_notificar, api_client, llaves):
    """Punto 3: Un dispositivo nuevo (distinto al historial) debe notificar."""
    user = Usuario.objects.create_user(
        email="nuevo@example.com", password="Password123!",
        first_name="Test", last_name="User", estado=Estado.ACTIVO
    )
    
    # Creamos un historial exitoso desde Firefox en Mac (dispositivo viejo)
    RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_FIREFOX_MAC, exitoso=True
    )
    
    url = reverse('auth:login')
    # Ahora entra desde Chrome en Windows (dispositivo nuevo)
    response = api_client.post(
        url, {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT=UA_CHROME_WINDOWS
    )
    
    assert response.status_code == 200
    mock_notificar.assert_called_once()

@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_dispositivo_conocido_no_notifica(mock_notificar, api_client, llaves):
    """Punto 3: Un dispositivo conocido (en los últimos 90 días) NO debe notificar."""
    user = Usuario.objects.create_user(
        email="conocido@example.com", password="Password123!",
        first_name="Test", last_name="User", estado=Estado.ACTIVO
    )
    
    # Creamos un registro reciente (10 días) desde Chrome en Windows
    registro = RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_CHROME_WINDOWS, exitoso=True
    )
    RegistroAcceso.objects.filter(pk=registro.pk).update(
        fecha=timezone.now() - timedelta(days=10)
    )
    
    url = reverse('auth:login')
    response = api_client.post(
        url, {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT=UA_CHROME_WINDOWS
    )
    
    assert response.status_code == 200
    mock_notificar.assert_not_called()

@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_dispositivo_mayor_90_dias_notifica(mock_notificar, api_client, llaves):
    """Punto 1: Un registro con más de 90 días de antigüedad NO cuenta como conocido."""
    user = Usuario.objects.create_user(
        email="viejo@example.com", password="Password123!",
        first_name="Test", last_name="User", estado=Estado.ACTIVO
    )
    
    # Creamos un registro con 100 días de antigüedad
    registro = RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_CHROME_WINDOWS, exitoso=True
    )
    RegistroAcceso.objects.filter(pk=registro.pk).update(
        fecha=timezone.now() - timedelta(days=100)
    )
    
    url = reverse('auth:login')
    response = api_client.post(
        url, {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT=UA_CHROME_WINDOWS
    )
    
    assert response.status_code == 200
    mock_notificar.assert_called_once()  # Debe notificar porque > 90 días

@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_intento_fallido_no_marca_como_conocido(mock_notificar, api_client, llaves):
    """Punto 2: Un intento fallido no debe marcar el dispositivo como conocido."""
    user = Usuario.objects.create_user(
        email="fallido@example.com", password="Password123!",
        first_name="Test", last_name="User", estado=Estado.ACTIVO
    )
    
    # Creamos un historial exitoso desde Firefox en Mac
    RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_FIREFOX_MAC, exitoso=True
    )
    # Registramos un intento FALLIDO desde Chrome en Windows (reciente)
    RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_CHROME_WINDOWS, exitoso=False
    )
    
    url = reverse('auth:login')
    # Ahora login exitoso desde Chrome en Windows (solo había fallo)
    response = api_client.post(
        url, {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT=UA_CHROME_WINDOWS
    )
    
    assert response.status_code == 200
    mock_notificar.assert_called_once()  # Debe notificar porque el fallo no cuenta

@pytest.mark.django_db
@patch('usuarios.tokens.notificar')
def test_mismo_navegador_distinto_so_notifica(mock_notificar, api_client, llaves):
    """Punto 3: Chrome en Windows vs Chrome en Mac deben ser dispositivos distintos."""
    user = Usuario.objects.create_user(
        email="so@example.com", password="Password123!",
        first_name="Test", last_name="User", estado=Estado.ACTIVO
    )
    
    # Registro exitoso desde Chrome en Windows (reciente)
    registro = RegistroAcceso.objects.create(
        usuario=user, dispositivo=DISPOSITIVO_CHROME_WINDOWS, exitoso=True
    )
    RegistroAcceso.objects.filter(pk=registro.pk).update(
        fecha=timezone.now() - timedelta(days=10)
    )
    
    url = reverse('auth:login')
    # Login desde Chrome en Mac (mismo navegador, distinto SO)
    response = api_client.post(
        url, {'email': user.email, 'password': 'Password123!'},
        HTTP_USER_AGENT=UA_CHROME_MAC
    )
    
    assert response.status_code == 200
    mock_notificar.assert_called_once()  # Dispositivo nuevo (distinto SO)