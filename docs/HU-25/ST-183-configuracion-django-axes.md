# **ST-183 — Instalar y configurar django-axes**

## **Estado**
Implementada y validada localmente.

## **Responsable**
Daniel Gómez Villaseñor (`gomez-d`).

## **Descripción**
Instalar y configurar `django-axes` para proteger el servicio de usuarios contra intentos fallidos de autenticación.

La configuración contempla:
- Límite de 5 intentos fallidos de autenticación.
- Tiempo de enfriamiento de 15 minutos.
- Identificación del bloqueo mediante la combinación de usuario e IP.
- Reinicio del contador después de una autenticación exitosa.

## **Resultado**
Se agrega `django-axes==9.0.0` como dependencia del proyecto.

En `config/settings.py` se incorpora:
- La aplicación `axes` en `INSTALLED_APPS`.
- `AxesMiddleware` al final de `MIDDLEWARE`.
- `AxesStandaloneBackend` en `AUTHENTICATION_BACKENDS`, conservando los backends de autenticación existentes.
- Los parámetros `AXES_FAILURE_LIMIT`, `AXES_COOLOFF_TIME`, `AXES_LOCKOUT_PARAMETERS` y `AXES_RESET_ON_SUCCESS`.
- `AXES_USERNAME_CALLABLE`, para obtener correctamente el identificador utilizado durante la autenticación.

### Corrección en la identificación de intentos fallidos

Durante la validación se identificó que los intentos fallidos podían registrarse con `username=None`. Esto ocurría porque el flujo de autenticación enviaba el identificador mediante la clave `username`, mientras que Axes esperaba obtenerlo mediante `email`.

Para corregirlo:
- Se creó `usuarios/axes.py`.
- Se implementó `obtener_usuario_axes`, que recupera el identificador desde las credenciales recibidas (`username` o `email`) y contempla los datos de la petición (`request.data` o `request.POST`) como respaldo.
- Se configuró `AXES_USERNAME_CALLABLE` para que Axes utilice dicha función.

Con esta corrección, los intentos fallidos pueden asociarse al identificador de la cuenta y combinarse con la IP para aplicar el bloqueo configurado.

### Validaciones

La configuración quedó validada localmente mediante las siguientes comprobaciones:

- `pip install -r requirements.txt`: dependencias instaladas correctamente.
- `python manage.py check`: sin problemas del sistema.
- `docker compose build`: imagen construida correctamente.
- `docker compose run --rm api python manage.py migrate`: migraciones aplicadas correctamente.
- `docker compose run --rm api python manage.py showmigrations axes`: las 10 migraciones de django-axes aparecen aplicadas.
- `docker compose run --rm api ruff check .`: todas las comprobaciones pasaron.
- `docker compose run --rm api python manage.py makemigrations --check --dry-run`: no se detectaron cambios.
- `docker compose run --rm api pytest`: 67 pruebas pasaron.

Además, durante la corrección de la identificación de intentos fallidos se verificaron las siguientes pruebas existentes:

- Cinco intentos fallidos reales: la cuenta aparece bloqueada.
- Intentos por debajo del límite: la cuenta no aparece bloqueada.
- Después del periodo de enfriamiento: la cuenta deja de aparecer bloqueada.

Las tres pruebas pasaron después de corregir la configuración.

## **Alcance**
Esta subtarea corresponde a la instalación y configuración de `django-axes`, incluida la corrección necesaria para identificar los intentos fallidos de autenticación.

La respuesta de error estándar para el bloqueo corresponde a ST-184. Las pruebas específicas asignadas a la subtarea ST-185 quedan fuera del alcance de ST-183. Las pruebas existentes ejecutadas durante esta subtarea se utilizaron como validación de la configuración implementada.
