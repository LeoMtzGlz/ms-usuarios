# ST-181 · Pruebas del límite de solicitudes

| | |
| --- | --- |
| **Historia** | HU-24 · Limitar las solicitudes a los endpoints públicos |
| **Responsable** | l22420429 |
| **Rama** | `t-24/st-181` |
| **Estado** | En revisión |

## Descripción

Pruebas de "límite + 1 devuelve 429" sobre los endpoints reales de HU-24, usando la caché de PostgreSQL (st-178), los scopes por IP (st-179) y el throttle por cuenta (st-180).

Archivo: `usuarios/tests/test_throttle_endpoints.py`.

## Qué se prueba

| Endpoint | Límite por IP | Límite por cuenta |
| --- | --- | --- |
| `POST /api/v1/auth/login/` | 10 por minuto | no aplica |
| `POST /api/v1/auth/registro/` | 5 por hora | no aplica |
| `POST /api/v1/auth/recuperar/` | 3 por hora | 3 por hora |
| `POST /api/v1/auth/reenviar-codigo/` | 3 por hora | 3 por hora |

- La solicitud límite + 1 responde **429** con `Retry-After` mayor a 0.
- Otra IP no comparte el contador.
- La misma cuenta desde IPs distintas también se bloquea en la cuarta solicitud.
- `ANA@mail.com`, `ana@mail.com` y `" Ana@Mail.com "` cuentan como la misma cuenta; igual `443 123 4567` y `+524431234567`.
- Recuperar y reenviar llevan contadores por cuenta separados.
- Los contadores quedan en `cache_table` de PostgreSQL y la clave por cuenta no contiene el correo en claro.

Las pruebas por cuenta usan correos que no existen a propósito: así responde el throttle y no el límite manual por cuenta de reenviar (st-76/st-77), que solo aplica a cuentas pendientes.

## Cambios en vistas

Al escribir las pruebas, 5 de 11 fallaban: `ThrottlePorCuenta` no estaba conectado a ninguna vista y reenviar no tenía scope por IP. Se agregó:

- `usuarios/views_recuperacion.py`: `throttle_classes = [ScopedRateThrottle, ThrottlePorCuenta]`.
- `usuarios/reenvio.py`: `throttle_scope = "reenviar"` y `throttle_classes = [ScopedRateThrottle, ThrottlePorCuenta]`.

`ScopedRateThrottle` va en la lista porque `throttle_classes` reemplaza a `DEFAULT_THROTTLE_CLASSES`; sin él se perdería el límite por IP.

## Archivos

- `usuarios/tests/test_throttle_endpoints.py` (nuevo)
- `usuarios/views_recuperacion.py` (2 líneas)
- `usuarios/reenvio.py` (2 líneas)
- No toca `settings.py`, `urls.py`, `requirements.txt` ni migraciones.

## Pendiente fuera de esta subtarea

- La tabla `cache_table` sigue sin crearse en Docker ni en el servidor. Las pruebas la crean con `createcachetable`; en el servidor hay que correr `python manage.py createcachetable` una vez.

## Resultado

`ruff check .`, `makemigrations --check --dry-run` y `pytest` (792 pasan, 2 fallos esperados que ya existían) pasan en local con Docker.
