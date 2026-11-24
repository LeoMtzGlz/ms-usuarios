# ST-183 — Instalar y configurar django-axes

## Estado
Implementada y validada localmente.

## Responsable
Daniel Gómez Villaseñor (`gomez-d`).

## Descripción
Instalar y configurar `django-axes` para proteger el servicio de usuarios contra intentos fallidos de autenticación.

La configuración contempla:
- Límite de 5 intentos fallidos de autenticación.
- Tiempo de enfriamiento de 15 minutos.
- Identificación del bloqueo mediante la combinación de usuario e IP.
- Reinicio del contador después de una autenticación exitosa.

## Resultado
Se agrega `django-axes==9.0.0` como dependencia del proyecto.

En `config/settings.py` se incorpora:
- La aplicación `axes` en `INSTALLED_APPS`.
- `AxesMiddleware` al final de `MIDDLEWARE`.
- `AxesStandaloneBackend` en `AUTHENTICATION_BACKENDS`, conservando `ModelBackend`.
- Los parámetros `AXES_FAILURE_LIMIT`, `AXES_COOLOFF_TIME`, `AXES_LOCKOUT_PARAMETERS` y `AXES_RESET_ON_SUCCESS`.

La configuración quedó validada localmente mediante las siguientes comprobaciones:

- `pip install -r requirements.txt`: dependencias instaladas correctamente.
- `python manage.py check`: sin problemas del sistema.
- `docker compose build`: imagen construida correctamente.
- `docker compose run --rm api python manage.py migrate`: migraciones aplicadas correctamente.
- `docker compose run --rm api python manage.py showmigrations axes`: las 10 migraciones de django-axes aparecen aplicadas.
- `docker compose run --rm api ruff check .`: todas las comprobaciones pasaron.
- `docker compose run --rm api python manage.py makemigrations --check --dry-run`: no se detectaron cambios.
- `docker compose run --rm api pytest`: 67 pruebas pasaron.

La validación integral del bloqueo para inicio de sesión con correo y teléfono depende de la integración del flujo de login de HU-05. Esta subtarea no modifica el endpoint ni la lógica de autenticación de dicha historia.

La respuesta de error estándar para el bloqueo corresponde a ST-184 y las pruebas específicas de bloqueo y enfriamiento corresponden a ST-185; no forman parte del alcance de ST-183.