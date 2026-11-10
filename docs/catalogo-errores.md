# Catálogo de códigos de error
 
Toda respuesta de error de la API tiene esta forma:
 
```json
{"codigo": "datos_invalidos", "mensaje": "Revisa los datos enviados.", "campos": {"email": ["Este correo ya está registrado."]}}
```
 
- `codigo`: identificador estable para que el frontend decida qué hacer. Nunca cambia de nombre.
- `mensaje`: texto en español para mostrar a la persona.
- `campos`: solo en errores de validación; cada campo con su lista de mensajes.
 
| Código | HTTP | Cuándo | Qué debe hacer el frontend |
| --- | --- | --- | --- |
| `datos_invalidos` | 400 | Falta un campo o tiene formato incorrecto | Mostrar cada mensaje junto a su campo |
| `codigo_invalido` | 400 | El código de 6 dígitos no coincide | Pedir que lo revise; quedan intentos |
| `codigo_expirado` | 400 | El código venció, ya se usó o agotó sus 5 intentos | Ofrecer pedir otro |
| `no_autenticado` | 401 | La petición no trae token | Ir al login |
| `credenciales_invalidas` | 401 | Correo, teléfono o contraseña incorrectos (no dice cuál) | Mostrar el mensaje genérico |
| `token_invalido` | 401 | Token vencido, alterado, en lista negra o de una sesión cerrada | Renovar con el refresh o ir al login |
| `sin_permiso` | 403 | El rol no permite la acción | Ocultar la opción |
| `cuenta_pendiente` | 403 | Contraseña correcta pero la cuenta no se ha activado | Llevar a la pantalla de activación |
| `cuenta_inactiva` | 403 | El administrador desactivó la cuenta | Indicar que contacte al administrador |
| `cuenta_bloqueada` | 403 | 5 intentos fallidos; bloqueo de 15 minutos | Indicar que espere |
| `debe_cambiar_password` | 403 | Tiene contraseña temporal | Llevar a cambiar la contraseña |
| `no_encontrado` | 404 | La ruta o el recurso no existen | Mostrar "no encontrado" |
| `metodo_no_permitido` | 405 | Método HTTP equivocado | Error de programación del cliente |
| `demasiados_intentos` | 429 | Se rebasó el límite de solicitudes; trae `Retry-After` | Esperar los segundos indicados |
| `error_interno` | 500 | Error inesperado del servidor; queda en el log | Mostrar "intenta más tarde" |
 
Las clases de Python que producen cada código están en `comun/errores.py`.
