# T-10 · Diseño: reintentos y respaldo de la bandeja de salida (ST-52, ST-53, ST-54)

**Tarea:** T-10 · Procesar la bandeja de salida con reintentos y respaldo de canal
**Responsable:** Santiago Mora (santiago-amn)
**Estado:** aprobado el 2026-11-22. Cubre las tres subtareas; cada una tiene su propio documento en esta carpeta.

## Para qué

Hoy `manejar_fallo()` (ST-51) marca la notificación como fallida al primer error. Un código de activación o de recuperación se pierde si WhatsApp falla un instante, y la persona se queda sin poder entrar. T-10 hace que el worker reintente, y que cuando WhatsApp no responde el mismo mensaje salga por correo. Bloquea a HU-03 (activar la cuenta), de l22420385.

## Objetivos

- **ST-52:** reintentos (`intentos += 1`) y respaldo a correo, sin enviar nunca un código vencido.
- **ST-53:** servicio `worker` en `docker-compose.yml` que corre `procesar_notificaciones`.
- **ST-54:** pruebas del worker: éxito, fallo con reintento, respaldo a correo y código vencido.

## Fuera de alcance

- Espera entre reintentos (backoff). Un reintento ocurre en el siguiente ciclo de 5 s.
- La clase `CanalWhatsApp` (T-09) y el límite diario por canal (T-11 / ST-57, que usa `antes_de_enviar()`).
- Cambiar el modelo `Notificacion` o agregar migraciones.
- Tocar `usuarios/codigos.py` o quien crea las notificaciones.

## Qué sería un fracaso aunque funcione

- Que una persona reciba un código vencido, o el mismo mensaje dos veces por el mismo canal.
- Que el código en claro quede guardado en una notificación que ya no se va a enviar.
- Que un fallo de una notificación tumbe al worker o detenga al resto del lote.

## Restricciones

- `procesar()` y `manejar_fallo()` conservan su forma actual (`manejar_fallo(notificacion, exc)`); `antes_de_enviar()` sigue siendo el punto de ST-57.
- Sin migraciones: la vida del código sale de `creado_en` y `contexto["minutos"]`.
- El worker sigue siendo el mismo comando; en Docker es la misma imagen que la API con otro comando.

## Enfoques considerados

| Enfoque | Qué cambia | Por qué sí o no |
| --- | --- | --- |
| **A. Reintentar en el siguiente ciclo, sin espera** | `intentos += 1` y la fila sigue pendiente | **Elegido.** Es lo que piden la ST-51 y Notion; no necesita migración. Riesgo: una caída corta del proveedor agota los 3 intentos en unos 15 s |
| B. Campo `proximo_intento_en` | Migración y filtro en `tomar_pendientes()` | Da espera real, pero toca el modelo (lo fusiona el profesor) y nadie lo pidió |
| C. Espera calculada con `actualizado_en` | Filtro en `tomar_pendientes()`, sin migración | Posible más adelante; agrega una regla de tiempo que la ST-52 no pide |

## Decisiones

- **«3 reintentos» = 3 fallos en total**, como dice la ST-51 («hasta 3 fallos»). Con `intentos < 3` la notificación sigue pendiente; al tercer fallo se resuelve. Decisión mía, no acordada con el equipo.
- **Respaldo solo desde WhatsApp.** Al tercer fallo de una notificación de WhatsApp se crea la misma notificación por correo (misma plantilla y contexto, `intentos = 0`, pendiente) y la original queda `fallida`. Una de correo o consola que falla 3 veces queda `fallida` sin copia.
- **La copia conserva el `creado_en` de la original** (se fija con una actualización de consulta, porque `auto_now_add` lo ignora al crear). Así el respaldo no alarga la vida del código.
- **Código vencido:** una notificación con `codigo` y `minutos` en el contexto vence a los `minutos` desde `creado_en`. Si venció, no se envía ni se reintenta ni se respalda: queda `fallida` con el error «Código vencido», y el `contexto` se vacía (lleva el código). Las notificaciones sin código no se ven afectadas.
- **Código tapado en el error y vaciado al terminar:** cuando una notificación queda `fallida` de forma definitiva, su `contexto` se vacía, igual que al enviarse. La copia de respaldo conserva el suyo.
- **ST-53:** servicio `worker` con la misma imagen y `.env` que `api`, comando `python manage.py procesar_notificaciones`, `restart: unless-stopped`, esperando a que la base esté sana, y sin puertos.

## Lo que queda al implementador

- Los nombres internos de las funciones auxiliares y el texto exacto de los errores y de los logs.
- Cómo estructurar las pruebas, mientras cubran lo listado en ST-54.
- Si `stop_grace_period` del servicio hace falta para que el SIGTERM termine el lote en curso.
