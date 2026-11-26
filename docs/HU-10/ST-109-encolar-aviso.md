# HU-10 — Recuperar mi contraseña

## ST-109. Encolar el aviso de contraseña cambiada

**Estado:** Completada  
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción
Se agregó la llamada a `notificar()` dentro del endpoint de restablecer contraseña para que, al finalizar exitosamente, se encole un correo de aviso al usuario informando que su contraseña ha sido cambiada.

### 2. Cambios realizados
| Archivo | Cambio |
|---|---|
| `usuarios/restablecer.py` | Se agregó la llamada a `notificar(plantilla="password_cambiada")`. |
| `usuarios/tests/test_restablecer.py` | Se agregó prueba para verificar la creación de la notificación. |

### 3. Resultado
El flujo de recuperación ahora notifica al usuario por correo tras un cambio exitoso.