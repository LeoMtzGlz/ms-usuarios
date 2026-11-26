# **ST-194 – Respuestas idénticas para cuenta existente e inexistente**

**Estado:** Implementada, pendiente de revisión
**Responsable:** Daniel Gómez Villaseñor (gomez-d)
**Subtarea:** ST-194

## **Descripción**

Se agregó una prueba para verificar que el endpoint de login devuelva respuestas idénticas cuando se proporciona una contraseña incorrecta, tanto para una cuenta existente como para una inexistente. El objetivo es evitar que la respuesta de autenticación revele información sobre la existencia de una cuenta.

## **Implementación**

- Se agregó una prueba en `usuarios/tests/test_login.py`.
- Se realizaron dos solicitudes al endpoint `/api/v1/auth/login/`: una utilizando el correo de una cuenta existente y otra utilizando un correo inexistente.
- En ambas solicitudes se utilizó una contraseña incorrecta.
- Se verificó que las dos respuestas tengan el código HTTP `401`.
- Se comparó el contenido completo de ambas respuestas para comprobar que sean idénticas.

## **Resultado**

La prueba confirma que el endpoint de login devuelve el mismo código HTTP y el mismo contenido de respuesta ante credenciales incorrectas, independientemente de que la cuenta proporcionada exista o no. Con ello se evita revelar información sobre la existencia de cuentas mediante este flujo de autenticación.

El alcance de esta implementación corresponde a la comparación de respuestas del login.

## **Validaciones**

- `ruff check .`: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `python manage.py migrate`: migraciones aplicadas correctamente.
- `usuarios/tests/test_login.py`: 5 pruebas aprobadas.
- `pytest`: 325 pruebas aprobadas en 24.20 segundos.