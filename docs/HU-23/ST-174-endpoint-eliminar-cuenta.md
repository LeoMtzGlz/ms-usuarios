# ST-174: Crear el endpoint de eliminación

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Historia:** HU-23 · Eliminar mi cuenta
**Descripción:** `POST /api/v1/auth/eliminar-cuenta/` pide la contraseña y la palabra `ELIMINAR`, envía un correo de confirmación y anonimiza la cuenta con `anonimizar_usuario()` (ST-173).

## Petición
Requiere sesión iniciada (Bearer token).
```json
{"password": "MiContraseña2026", "confirmacion": "ELIMINAR"}
```

## Respuestas
| Caso | HTTP | `codigo` |
| --- | --- | --- |
| Cuenta eliminada | 200 | — (`{"mensaje": "Tu cuenta fue eliminada."}`) |
| Contraseña incorrecta, o falta/está mal la palabra `ELIMINAR` | 400 | `datos_invalidos` (con `campos`) |
| Sin token | 401 | `no_autenticado` |
| Es el único administrador activo | 403 | `unico_administrador` |

## Orden (ST-172 §3)
1. Validar contraseña y palabra `ELIMINAR` (exacta, en mayúsculas).
2. Si el rol es administrador y no hay otro administrador activo, responde 403 sin cambiar nada.
3. Guardar el correo original y enviarle el correo de confirmación.
4. `anonimizar_usuario()`: datos personales anonimizados, cuenta inactiva, sesiones cerradas.

Todo dentro de una transacción; si algo falla antes de anonimizar, la cuenta queda intacta.

## Decisión sobre el correo de confirmación (ST-172 §4.1)
El worker lee `usuario.email` al enviar; tras anonimizar, el correo ya no llegaría. Mientras el equipo no decide la opción A (campo `destino` en `Notificacion`), se usa la **opción B**: el correo se envía directo por `CanalCorreo` al correo original, antes de anonimizar. Si el envío falla, se registra en el log y la eliminación continúa. Cuando se implemente la opción A, solo hay que cambiar `enviar_confirmacion()` en `usuarios/eliminacion.py`.

## Archivos
- Nuevos: `usuarios/eliminacion.py`, `usuarios/views_eliminacion.py`, `notificaciones/templates/notificaciones/correo/cuenta_eliminada.html`, `usuarios/tests/test_eliminar_cuenta.py`.
- Modificados: `usuarios/serializers.py` (`EliminarCuentaSerializer`), `usuarios/urls.py`, `comun/errores.py` (`UnicoAdministrador`), `notificaciones/plantillas.py` (plantilla `cuenta_eliminada`), `notificaciones/tests/test_plantillas_correo.py` (de 5 a 6 plantillas), `docs/catalogo-errores.md`.

## Pruebas
docker compose run --rm api pytest usuarios/tests/test_eliminar_cuenta.py -v