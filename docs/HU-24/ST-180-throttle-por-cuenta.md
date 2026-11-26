# ST-180 · Crear el throttle por cuenta

| | |
| --- | --- |
| **Historia** | HU-24 · Limitar las solicitudes a los endpoints públicos |
| **Responsable** | l22420429 |
| **Rama** | `hu-24/st-180` |
| **Estado** | En revisión |

## Descripción

Throttle de DRF que usa como clave el correo o teléfono que llega en el body, no la IP. Así quien cambia de IP no puede pedir más códigos para la misma cuenta. Es el límite "por cuenta" de HU-24 para recuperar contraseña y reenviar código (3 por hora).

Archivo: `comun/throttles.py` → `ThrottlePorCuenta`.

## Cómo funciona

- Busca la cuenta en el body en este orden: `correo`, `email`, `telefono`, `identificador`.
- La normaliza igual que el modelo: correo sin espacios y en minúsculas; teléfono en E.164. Así `ANA@mail.com` y `ana@mail.com`, o `443 123 4567` y `+524431234567`, cuentan como la misma cuenta. Un teléfono inválido también gasta intentos.
- Si el body no trae cuenta, no limita (queda el límite por IP de st-179).
- Cada endpoint tiene su propio contador: la clave incluye el `throttle_scope` de la vista.
- La clave guarda un hash SHA-256 de la cuenta, no el correo ni el teléfono en claro.
- Límite: `3/hour`. Se puede cambiar con `DEFAULT_THROTTLE_RATES["cuenta"]` sin tocar el código.
- Los contadores van en la caché de PostgreSQL (t-24/st-178).
- Al pasar el límite responde **429** con `Retry-After` y el formato estándar (`demasiados_intentos`), que ya maneja `comun/errores.py`.

## Cómo usarlo en un endpoint

```python
from rest_framework.throttling import ScopedRateThrottle
from comun.throttles import ThrottlePorCuenta

class ReenviarCodigoView(APIView):
    throttle_scope = "reenviar_codigo"   # el de st-179 (límite por IP)
    throttle_classes = [ScopedRateThrottle, ThrottlePorCuenta]
```

Los endpoints de recuperar (HU-10) y reenviar código (HU-04) todavía no existen; sus responsables agregan `ThrottlePorCuenta` a `throttle_classes`.

## Archivos

- `comun/throttles.py` (nuevo)
- `comun/tests/test_throttle_por_cuenta.py` (nuevo)
- No toca `settings.py`, `urls.py`, `requirements.txt` ni migraciones.

## Pendiente fuera de esta subtarea

- La tabla `cache_table` de la caché en PostgreSQL no se crea en ningún lado (ni Docker ni CI). Las pruebas la crean con `createcachetable`, pero en el servidor hay que correr `python manage.py createcachetable` una vez. Se avisó al responsable de T-24.
- Acordar con st-179 el nombre de los scopes por IP de recuperar y reenviar.

## Resultado

`ruff check .`, `makemigrations --check --dry-run` y `pytest` pasan en local.