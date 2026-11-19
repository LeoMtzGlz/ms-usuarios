# **ST-184 – Responder con el formato de error estándar**

**Estado:** Implementada, pendiente de revisión  
**Responsable:** Daniel Gómez Villaseñor (gomez-d)  
**Subtarea:** ST-184

## **Descripción**

Se implementó un handler propio para que django-axes responda con el formato estándar de errores de la API cuando una cuenta sea bloqueada por intentos fallidos de inicio de sesión.

## **Implementación**

- Se implementó `respuesta_bloqueo_axes` en `comun/errores.py`.
- Se reutilizó la excepción `CuentaBloqueada` para mantener el código y mensaje estándar del bloqueo.
- Se configuró `AXES_LOCKOUT_CALLABLE` en `config/settings.py` para conectar django-axes con el handler personalizado.
- Se agregó una prueba en `comun/tests/test_errores.py` para verificar el formato de la respuesta.
- Se estableció el estado HTTP `403 Forbidden`.
- Se mantuvo la estructura estándar de respuesta: `codigo`, `mensaje` y `campos`.

## **Resultado**

Cuando django-axes ejecuta el handler personalizado, la API devuelve una respuesta con el formato estándar de errores, utilizando el código `cuenta_bloqueada`, el mensaje correspondiente y un objeto `campos` vacío.

Queda pendiente realizar una prueba de integración del bloqueo mediante el endpoint de inicio de sesión, una vez que dicho endpoint esté disponible en `development`, así como verificar el comportamiento completo de los intentos fallidos y el periodo de enfriamiento.

## **Validaciones**

- `ruff check .`: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `python manage.py migrate`: migraciones aplicadas correctamente.
- `pytest`: 176 pruebas aprobadas.
- `comun/tests/test_errores.py`: 9 pruebas aprobadas.
- `git diff --check`: sin errores.