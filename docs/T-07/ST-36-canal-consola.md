# T-07 — Crear la bandeja de salida de notificaciones en PostgreSQL

## ST-36. Crear el canal de consola para desarrollo (y ajustes de ST-35)

**Estado:** Completada (en espera de revisión)
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción

Se implementó el `CanalConsola` para imprimir las notificaciones en la terminal durante el desarrollo (sin usar proveedores externos). Además, atendiendo a las observaciones del profesor sobre la ST-35, se agregó la configuración por *setting* para elegir el canal, la validación con `ValueError` para canales inválidos y una prueba que asegura el uso del `canal_preferido` del usuario.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/canales.py` | Creación de la clase `CanalConsola` que implementa `Canal`. |
| `notificaciones/services.py` | Función `obtener_canal()` que lee el setting; validación `ValueError` en `notificar()`. |
| `notificaciones/tests/test_services.py` | Pruebas para el canal preferido y el error de canal inválido. |
| `config/settings.py` | Nuevo setting `CANAL_NOTIFICACIONES = env("CANAL_NOTIFICACIONES", default="consola")`. |
| `.env.example` | Variable `CANAL_NOTIFICACIONES=consola`. |
| `docs/T-07/ST-36-canal-consola.md` | Documentación de esta subtarea. |

### 3. Qué hace el canal y las validaciones

**Selección de canal por setting:**
La función `obtener_canal()` lee la variable `CANAL_NOTIFICACIONES`. Si está configurada como `consola`, devuelve una instancia de `CanalConsola`. En el futuro, Alondra y el equipo de WhatsApp agregarán sus clases aquí.

**Validación de canales:**
Si alguien intenta llamar a `notificar()` con un canal que no existe (por ejemplo, `"telegram"`), el sistema lanza un `ValueError` inmediatamente, evitando que se guarden datos corruptos en la base de datos.

**Pruebas añadidas:**
1. `test_notificar_usa_canal_preferido_si_no_se_envia`: Verifica que si no pasas el parámetro `canal`, toma el del usuario.
2. `test_notificar_lanza_error_si_canal_es_invalido`: Verifica que lanza un `ValueError` si el canal no está en `CanalNotificacion.values`.

### 4. Coordinación con otros equipos

Se notificó a Alondra (responsable de T-08) que la interfaz `Canal` ya está lista y que su clase `CanalCorreo` debe heredar de ella e implementar la firma exacta: `def enviar(self, destino: str, asunto: str, texto: str) -> None:`.

### 5. Resultado

Todas las pruebas pasan en verde (`4 passed`). El código cumple con las observaciones del profesor y está listo para ser fusionado. El canal de consola permitirá al equipo probar el flujo de notificaciones localmente sin depender de correos reales.

**ST-36 finalizada.**

**Responsable de la actividad:** Katia Paola Victoria Escalera.