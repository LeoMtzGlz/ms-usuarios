# ST-62 — Pruebas del canal de notificaciones

## Estado
Implementado y validado localmente.

## Responsable
Daniel Gómez Villaseñor (`gomez-d`).

## Descripción
Se agregaron pruebas para verificar la selección del canal de notificaciones en los flujos de recuperación de contraseña y reenvío de códigos.

Los escenarios cubiertos son:
- Uso del canal solicitado explícitamente.
- Uso del canal preferido del usuario cuando no se indica uno.
- Respaldo a correo cuando WhatsApp no está disponible porque el usuario no tiene teléfono, tanto cuando se utiliza el canal preferido como cuando se solicita WhatsApp explícitamente.

En los flujos de recuperación de contraseña y reenvío de códigos, la respuesta no informa si hubo un cambio de canal ni cuál fue el canal finalmente utilizado. En recuperación de contraseña, esta restricción evita revelar información que permita inferir si una cuenta existe.

## Archivos modificados
- `usuarios/tests/test_recuperar.py`
- `usuarios/tests/test_reenvio.py`

## Resultado de las validaciones
- Pruebas de usuarios y notificaciones: 564 aprobadas y 1 xfailed.
- Ruff: `All checks passed!`
- Migraciones: `No changes detected`.
- `git diff --check`: sin errores.

## Resultado
Los escenarios de selección y respaldo de canal quedaron cubiertos mediante pruebas automatizadas, incluyendo la solicitud explícita de WhatsApp sin teléfono. Se documentó que las respuestas no revelan cambios de canal ni el canal finalmente utilizado. No se requirieron cambios en la lógica de producción ni migraciones.
