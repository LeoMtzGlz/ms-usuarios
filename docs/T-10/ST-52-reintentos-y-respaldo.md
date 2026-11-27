# T-10 — Procesar la bandeja de salida con reintentos y respaldo de canal

## ST-52. Reintentos y respaldo a correo

**Estado:** En revisión  
**Diseño aprobado:** `docs/T-10/ST-52-diseno-reintentos-respaldo.md`

### 1. Descripción

El worker de ST-51 marcaba una notificación como `fallida` al primer error. Ahora la reintenta hasta
3 veces; si es de WhatsApp y falla las 3, crea una copia por correo para que el aviso llegue por otra vía.
También descarta los códigos que ya vencieron, sin enviarlos.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/worker.py` | `MAX_INTENTOS`, `codigo_vencido`, `crear_respaldo_por_correo`, `marcar_fallida` y nueva lógica de `manejar_fallo`; `procesar` revisa el vencimiento antes de `antes_de_enviar()` |
| `notificaciones/tests/test_reintentos_respaldo.py` | Pruebas de reintentos, respaldo y vencimiento |
| `notificaciones/tests/test_canal_por_notificacion.py` | Una aserción ajustada: WhatsApp sin clase queda `pendiente` tras el primer fallo |
| `notificaciones/tests/test_worker.py` | Dos pruebas ajustadas al nuevo comportamiento (el primer fallo ya no es definitivo) |

Sin migraciones ni cambios en modelos, `usuarios/codigos.py` o configuración.

### 3. Cómo funciona

| Canal | Fallos acumulados | Resultado |
|---|---|---|
| cualquiera | 1 o 2 | Sigue `pendiente`, `intentos` sube; se reintenta en el siguiente ciclo (5 s). Se conserva el contexto |
| WhatsApp | 3 | Original `fallida` con contexto vacío; copia nueva por `correo`, `pendiente`, `intentos` 0 |
| correo / consola | 3 | `fallida` con contexto vacío, sin copia |
| cualquiera, código vencido | (no se intenta) | `fallida`, error «Código vencido: no se envió», contexto vacío, sin copia |

Un código está vencido si tiene `codigo` y `minutos` en el contexto y `ahora > creado_en + minutos`.
Se revisa en `procesar()` antes de `antes_de_enviar()`. Si `minutos` falta, es `None`, no es numérico o no es finito (`nan`, `inf`),
no vence (nunca lanza error). Si vence entre el segundo y el tercer fallo, tampoco se crea la copia.

### 4. Decisiones

- **3 reintentos = 3 fallos en total** (`MAX_INTENTOS = 3`), sin espera entre uno y otro.
- **La copia conserva el `creado_en` original** (se fija con `update()` porque `auto_now_add` lo ignora al crear), así mantiene su lugar en la cola y el mismo vencimiento.
- **El error nunca lleva el código**: se limpia antes de vaciar el contexto. El contexto solo se vacía en el fallo definitivo.
- `procesar_lote` sigue contando cada intento fallido como `fallidas`, aunque la notificación quede pendiente.

- **Si falla el cierre definitivo** (crear la copia o marcar `fallida`, p. ej. error de base de datos), ambos pasos corren en un savepoint y se revierten juntos; se registra en el log (sin el código), la original queda `pendiente` con su contexto y se reintenta el cierre en el siguiente ciclo. El resto del lote sigue.

### 5. Qué no hace

- No hay espera creciente (backoff) entre reintentos.
- No hay respaldo desde correo o consola, ni a otro canal que no sea correo.
- No aplica el límite diario por canal; eso es ST-57 (`antes_de_enviar()` queda intacto).

### 6. Cómo comprobarlo

```bash
docker compose run --rm api pytest notificaciones/tests/test_worker.py notificaciones/tests/test_reintentos_respaldo.py -v
docker compose run --rm api pytest
```
