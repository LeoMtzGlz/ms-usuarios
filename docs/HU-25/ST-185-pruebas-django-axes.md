# ST-185 – Pruebas de integración y aislamiento de Django Axes

**Estado:** Implementada, pendiente de revisión
**Responsable:** Daniel Gómez Villaseñor (gomez-d)
**Subtarea:** ST-185

## Descripción

Se implementaron pruebas de integración para verificar el comportamiento del bloqueo temporal de cuentas mediante django-axes, incluyendo la permanencia del bloqueo después de cinco intentos fallidos y la posibilidad de iniciar sesión una vez transcurrido el periodo de enfriamiento.

También se aisló la configuración de django-axes para evitar que afecte las pruebas que no corresponden a esta funcionalidad.

## Implementación

- Se agregó el fixture `axes_desactivado_por_defecto` en `conftest.py` para desactivar django-axes automáticamente en las pruebas no relacionadas con bloqueos.
- Se agregó el fixture `axes_habilitado` para activar django-axes explícitamente en las pruebas que necesitan comprobar su comportamiento.
- Se habilitó django-axes en las pruebas existentes de `usuarios/tests/test_listar_usuarios.py` que verifican el estado de bloqueo de las cuentas.
- Se creó `usuarios/tests/test_bloqueo_axes.py` para concentrar las pruebas de integración de ST-185.
- Se agregó la prueba `test_sexto_intento_con_password_correcta_sigue_bloqueado` para comprobar que el sexto intento continúa bloqueado incluso cuando se proporciona la contraseña correcta.
- Se agregó la prueba `test_puede_iniciar_sesion_despues_del_enfriamiento` para comprobar que el usuario puede iniciar sesión después de transcurridos los 15 minutos de enfriamiento.
- Se reutilizó `PASSWORD_PRUEBA` de `usuarios/tests/factories.py` en las pruebas.
- Se actualizó la prueba de integración `test_bloqueo_por_drf_responde_403_estandar` en `comun/tests/test_errores.py` para habilitar django-axes explícitamente y conservar su comportamiento con el nuevo aislamiento.

## Resultado

Después de cinco intentos fallidos de inicio de sesión, un sexto intento con la contraseña correcta continúa bloqueado y devuelve HTTP `403 Forbidden`, utilizando el código `cuenta_bloqueada`.

Una vez transcurrido el periodo de enfriamiento de 15 minutos, el usuario puede iniciar sesión correctamente y recibe los tokens de acceso y actualización.

Las pruebas que no corresponden a django-axes quedan aisladas de su funcionamiento mediante la desactivación automática, mientras que las pruebas de bloqueo lo habilitan explícitamente.

## Validaciones

- `ruff check conftest.py usuarios/tests/test_listar_usuarios.py usuarios/tests/test_bloqueo_axes.py comun/tests/test_errores.py`: todos los checks aprobados.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `pytest usuarios/tests/test_bloqueo_axes.py`: 2 pruebas aprobadas.
- `pytest usuarios/tests/test_listar_usuarios.py`: 45 pruebas aprobadas.
- `pytest comun/tests/test_errores.py -k "bloqueo_por_drf_responde_403_estandar"`: 1 prueba aprobada.
- `pytest`: 709 pruebas aprobadas y 2 pruebas `xfail`.
