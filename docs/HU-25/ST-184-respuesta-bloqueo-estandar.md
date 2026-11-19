# ST-184 – Responder con el formato de error estándar

**Estado:** Implementada, pendiente de revisión  
**Responsable:** Daniel Gómez Villaseñor (gomez-d)  
**Subtarea:** ST-184

## Descripción

Se implementó un handler propio para que django-axes responda con el formato estándar de errores de la API cuando una cuenta sea bloqueada por intentos fallidos de inicio de sesión.

## Implementación

- Se implementó `respuesta_bloqueo_axes` en `comun/errores.py`.
- Se reutilizó la excepción `CuentaBloqueada` para mantener el código y mensaje estándar del bloqueo.
- Se configuró `AXES_LOCKOUT_CALLABLE` en `config/settings.py` para conectar django-axes con el handler personalizado.
- Se conectó la señal `user_locked_out` de django-axes desde `comun/apps.py`.
- Se implementó `marcar_bloqueo_en_request_django` en `comun/errores.py` para propagar la marca de bloqueo desde el objeto Request de Django REST Framework al `HttpRequest` original de Django. Esto permite que el middleware de django-axes aplique el formato estándar de respuesta en el flujo de autenticación con SimpleJWT.
- Se agregó una prueba de integración en `comun/tests/test_errores.py` utilizando el endpoint de inicio de sesión de `TokenObtainPairView`.
- Se estableció el estado HTTP `403 Forbidden` para las respuestas de cuenta bloqueada.
- Se mantuvo la estructura estándar de respuesta: `codigo`, `mensaje` y `campos`.

## Resultado

Cuando una cuenta alcanza el límite de intentos fallidos y django-axes activa el bloqueo, la API responde con HTTP `403 Forbidden` y el formato estándar de errores, utilizando el código `cuenta_bloqueada`, el mensaje correspondiente y un objeto `campos` vacío.

La prueba de integración verifica el comportamiento del bloqueo mediante el endpoint de inicio de sesión de SimpleJWT y confirma que la respuesta conserva la estructura estándar.

El alcance de esta subtarea no incluye las pruebas completas del comportamiento de los intentos fallidos ni del periodo de enfriamiento, correspondientes a ST-185.

## Validaciones

- `ruff check .`: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `python manage.py migrate`: sin migraciones pendientes.
- `pytest`: 177 pruebas aprobadas.
- `git diff --check`: sin errores.
