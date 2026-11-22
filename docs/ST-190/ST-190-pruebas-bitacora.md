# ST-190 · Pruebas de los flujos de la bitácora (HU-26)

Archivo de pruebas: `comun/tests/test_bitacora_flujos.py`.

## Qué cubren

1. `test_cada_flujo_crea_su_evento`: ejecuta cada flujo real (por su endpoint, método del modelo o comando) y comprueba que existe un `EventoAuditoria` con la acción, el usuario esperado y `resultado="ok"`.
2. `test_ningun_evento_guarda_la_contrasena`: tras registro, alta de usuario y cambio de contraseña con valores conocidos, ni esas contraseñas ni la temporal devuelta por el alta aparecen en `detalles` ni en `user_agent` de ningún evento.
3. `test_no_administrador_recibe_403_en_la_bitacora`: cliente y operativo reciben 403 `sin_permiso` en `GET /api/v1/auditoria/`; el administrador ve el evento vía `?accion=`.

## Flujos probados

| Acción | Flujo | Usuario del evento |
|---|---|---|
| `registro` | `POST /api/v1/auth/registro/` | la cuenta creada |
| `alta_usuario` | `POST /api/v1/usuarios/` | el administrador que da el alta |
| `password_cambiado` | `Usuario.cambiar_password()` | el usuario |
| `estado_cambiado` | `Usuario.cambiar_estado()` | el usuario |
| `privacidad_aceptada` | `POST /api/v1/auth/privacidad/aceptar/` | el usuario autenticado |
| `2fa_activacion_iniciada` | `POST /api/v1/auth/2fa/activar/` | el usuario autenticado |
| `2fa_activado` | `POST /api/v1/auth/2fa/confirmar/` (código correcto) | el usuario autenticado |
| `2fa_confirmacion_fallida` | `POST /api/v1/auth/2fa/confirmar/` (código incorrecto) | el usuario autenticado |
| `admin_creado` | comando `crear_admin` | el administrador creado |

Observación: `2fa_confirmacion_fallida` hoy se guarda con `resultado="ok"` porque el llamador (`usuarios/views_2fa.py`) no pasa `resultado`. Es de otra historia; la prueba refleja lo que el código registra hoy. Lo correcto sería `resultado="fallo"`.

## Flujos pendientes (de otras historias)

Todavía no llaman a `registrar_evento()`; cuando se implementen deben usar estas acciones (los nombres de recuperación y bloqueo son propuestos; los demás vienen del alcance de la HU).

| Flujo | Acción |
|---|---|
| Inicio de sesión correcto | `login` |
| Inicio de sesión fallido | `login_fallido` |
| Cierre de sesión | `logout` |
| Recuperación de contraseña (solicitud y restablecimiento) | `recuperacion_solicitada`, `recuperacion_completada` |
| Bloqueo de cuenta por intentos fallidos | `cuenta_bloqueada` |
| Fallo al enviar una notificación | `envio_fallido` |
