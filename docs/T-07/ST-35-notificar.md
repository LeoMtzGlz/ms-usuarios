# T-07 — Crear la bandeja de salida de notificaciones en PostgreSQL

## ST-35. Crear la función notificar() con la interfaz de canales

**Estado:** Completada (con ajustes finales en ST-36)  
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción

Se creó la función central `notificar()` que se encarga de guardar las notificaciones en la base de datos (patrón Outbox) para que ningún mensaje se pierda si el proveedor de correo o WhatsApp falla. Además, se definió la clase abstracta `Canal` que servirá como interfaz para que los futuros canales (correo y WhatsApp) implementen el método `enviar()`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/canales.py` | Creación de la clase abstracta `Canal` con el método `enviar()`. |
| `notificaciones/services.py` | Creación de la función `notificar()` que crea un registro en `Notificacion`. |
| `notificaciones/tests/test_services.py` | Pruebas unitarias para verificar el guardado en la bandeja. |
| `docs/T-07/ST-35-notificar.md` | Documentación de la subtarea. |

### 3. Qué hace la función

**La función `notificar(usuario, plantilla, contexto, canal=None)`:**
- Si no se especifica un `canal`, utiliza automáticamente el `canal_preferido` del usuario.
- Guarda el registro en la base de datos con estado `pendiente`.
- *(Ajuste posterior en ST-36)*: Valida que el canal exista en el Enum `CanalNotificacion` y lanza un `ValueError` si es inválido.

**La clase `Canal`:**
- Es una interfaz (ABC) que define el contrato `enviar(destino, asunto, texto)`. Alondra (T-08) la usará para crear su `CanalCorreo`.

### 4. Resultado

La función `notificar()` está lista y probada. El PR #34 fue aprobado, y el profesor solicitó tres ajustes (setting del canal, validación de ValueError y prueba de canal preferido) los cuales fueron implementados en la subtarea ST-36.

**ST-35 finalizada.**

**Responsable de la actividad:** Katia Paola Victoria Escalera.