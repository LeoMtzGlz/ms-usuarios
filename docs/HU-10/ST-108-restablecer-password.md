# HU-10 — Recuperar mi contraseña con un código por correo o WhatsApp

## ST-108. Crear el endpoint POST /api/v1/auth/restablecer/

**Estado:** Completada  
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción

Se implementó el endpoint público `POST /api/v1/auth/restablecer/` que permite a un usuario establecer una nueva contraseña utilizando un código de verificación de 6 dígitos previamente enviado a su correo o teléfono. 

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/restablecer.py` | Creación del `RestablecerSerializer` y la vista `RestablecerPasswordView`. |
| `usuarios/urls.py` | Se agregó la ruta `restablecer/`. |
| `usuarios/tests/test_restablecer.py` | Se agregó la prueba de restablecimiento exitoso. |
| `docs/HU-10/ST-108-restablecer-password.md` | Documentación de esta subtarea. |

### 3. Comportamiento y seguridad

- **Validación del código:** Reutiliza la función `verificar_codigo()` de la ST-71. Verifica que el código no esté vencido, que no haya superado los 5 intentos y que no haya sido usado.
- **Validación de la contraseña:** Se asegura de que las contraseñas coincidan y que cumplan con la política de seguridad (`validate_password`).
- **Cierre de sesiones:** Al usar el método `cambiar_password()` del modelo `Usuario`, se incrementa automáticamente el `token_version`, lo que cierra todas las sesiones abiertas en otros dispositivos.
- **Respuesta:** Devuelve `200 OK` con el mensaje "Contraseña actualizada correctamente."

### 4. Resultado

El endpoint está funcionando correctamente y la prueba unitaria pasa en verde. El flujo de recuperación de contraseña queda completo (solicitud en ST-107, restablecimiento en ST-108).

**ST-108 finalizada.**