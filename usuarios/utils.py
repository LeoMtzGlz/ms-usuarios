import unicodedata
import random
import re
from django.conf import settings
from .models import Usuario

def quitar_acentos(texto):
    """Quita los acentos y diacríticos de un string."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def generar_correo_institucional(nombre, apellidos):
    """
    Genera un correo institucional único.
    Formato: letras del nombre y apellidos + 2 números + @dominio
    """
    # 1. Limpiar y unir nombre y apellidos
    nombre_limpio = quitar_acentos(nombre).lower()
    apellidos_limpio = quitar_acentos(apellidos).lower()
    
    # Quitar espacios y caracteres que no sean letras
    base = re.sub(r'[^a-z]', '', nombre_limpio + apellidos_limpio)
    
    # 2. Obtener el dominio desde el .env
    dominio = getattr(settings, 'DOMINIO_CORREO_INSTITUCIONAL', '@jiquilpan.tecnm.mx')
    
    # 3. Generar 2 números y verificar que no exista
    while True:
        numeros = random.randint(10, 99)
        correo = f"{base}{numeros}{dominio}"
        
        # Si el correo NO existe en la base de datos, lo devolvemos
        if not Usuario.objects.filter(email=correo).exists():
            return correo