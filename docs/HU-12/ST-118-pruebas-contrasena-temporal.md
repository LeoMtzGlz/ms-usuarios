# ST-118: Pruebas de la contraseña temporal (HU-12)

## Qué se prueba
Pruebas de punta a punta con el login, `cambiar-password` y los endpoints reales (no vistas de prueba).
Archivo: `usuarios/tests/test_contrasena_temporal.py` (24 pruebas).

| Escenario | Resultado esperado |
|---|---|
| Login con contraseña temporal | 200 y el access lleva `debe_cambiar_password = true` |
| Endpoints protegidos con ese token (`accesos`, `2fa/activar`, `2fa/confirmar`, `2fa/desactivar`) | 403, código `debe_cambiar_password` |
| `cambiar-password` con ese token | 200 |
| Renovar la sesión antes de cambiarla | El nuevo access sigue marcado |
| Cambio fallido (contraseña actual incorrecta) | 400 y la restricción se mantiene |
| Cambio exitoso | `debe_cambiar_password = false`, contraseña nueva válida |
| Tokens tras el cambio | Se emiten access y refresh nuevos, sin la marca |
| Endpoints con el token nuevo | Ya no responden 403 `debe_cambiar_password`; `accesos` da 200 |
| Refresh anterior | 401 (se invalida por `token_version`) |
| Refresh nuevo | Renueva sin la marca |
| Login posterior | La temporal da 401; la nueva da 200 sin la marca |
| Usuario con contraseña definitiva | Nunca recibe 403 `debe_cambiar_password` |
| Sin token | 401, no 403 |

## Notas
- El access anterior no se revoca (es de vida corta y sin estado), pero conserva la marca y sigue dando 403. Solo se invalida el refresh.
- `privacidad/aceptar` no se incluye: solo exige `IsAuthenticated`.
- No se modificó código de la aplicación.

## Cómo ejecutarlo
`docker compose exec api pytest usuarios/tests/test_contrasena_temporal.py -q`