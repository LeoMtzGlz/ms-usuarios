# HU-04 — Reenviar el código de activación

## ST-75. Crear el endpoint POST /api/v1/auth/reenviar-codigo/

**Estado:** Completada  
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción

Se implementó el endpoint público `POST /api/v1/auth/reenviar-codigo/` que permite a un usuario registrado (pero no activado) solicitar un nuevo código de 6 dígitos si no le llegó o si el anterior ya venció. La lógica invalida cualquier código previo pendiente del mismo propósito y encola uno nuevo utilizando la función `generar_codigo()` de la ST-71.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/reenvio.py` | Creación de la vista `ReenviarCodigoView` con la lógica de invalidación y generación del código. |
| `usuarios/urls.py` | Se agregó la ruta `reenviar-codigo/`. |
| `usuarios/tests/test_reenvio.py` | Se agregaron 3 pruebas unitarias (generación, respuesta genérica, cuenta activa). |
| `docs/HU-04/ST-75-reenviar-codigo.md` | Documentación de esta subtarea. |

### 3. Comportamiento y seguridad

- **Respuesta genérica:** Para evitar la enumeración de cuentas, la API siempre responde `200 OK` con el mensaje genérico: *"Si la cuenta existe y está pendiente, te enviamos un nuevo código."* No importa si el usuario existe o no.
- **Invalidación de código anterior:** Si se genera un nuevo código, el anterior se marca como `usado=True` dentro de una transacción para que no pueda ser reutilizado.
- **Solo cuentas pendientes:** La lógica solo dispara el envío del código si el usuario se encuentra en estado `PENDIENTE`. Si la cuenta está activa o inactiva, la respuesta es la misma pero no se envía nada.
- **Canales:** El endpoint acepta el parámetro opcional `canal` (correo o whatsapp) y se lo pasa a la función `generar_codigo()`.

### 4. Resultado

Todas las pruebas unitarias pasan en verde (`3 passed`). La integración con el sistema de notificaciones (Outbox) funciona correctamente.

**ST-75 finalizada.**