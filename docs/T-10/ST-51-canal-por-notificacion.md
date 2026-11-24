# T-10 — Procesar la bandeja de salida con reintentos y respaldo de canal

## ST-51. Enviar cada notificación por su propio canal

**Estado:** Completada (en espera de revisión)
**Responsable:** David Melgoza (22420429) Katia Paola (22420438)

### 1. Descripción

En la revisión del PR #53 el maestro pidió que `obtener_canal()` reciba el canal de cada
notificación (`obtener_canal(notificacion.canal)`), porque el worker llamaba
`obtener_canal()` sin argumentos y todas las notificaciones salían por el mismo canal: el
del setting `CANAL_NOTIFICACIONES`, sin importar si la notificación era de correo o de
WhatsApp.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/services.py` | `obtener_canal(canal=None)` recibe el canal y lo busca en el diccionario `CLASES_CANAL`. |
| `notificaciones/worker.py` | `procesar()` llama `obtener_canal(notificacion.canal)`. |
| `notificaciones/tests/test_worker.py` | El resolver falso `resolver_con()` acepta el canal. |
| `notificaciones/tests/test_canal_por_notificacion.py` | 5 pruebas nuevas. |
| `docs/T-10/ST-51-canal-por-notificacion.md` | Esta documentación. |

### 3. Cómo elige el canal

| `CANAL_NOTIFICACIONES` | Canal de la notificación | Sale por |
|---|---|---|
| `consola` (desarrollo) | cualquiera | consola |
| `correo` | `correo` | `CanalCorreo` |
| `correo` | `consola` | `CanalConsola` |
| `correo` | `whatsapp` | error `ValueError`: el worker la marca fallida |
| cualquiera | sin argumento: `obtener_canal()` | el del setting, como antes |

- En desarrollo todo sigue saliendo por consola, así nadie necesita la contraseña del correo
  para probar.
- Un canal que todavía no tiene clase (WhatsApp hasta T-09) no se manda en silencio por otro
  medio: queda fallida con el motivo `No hay canal disponible para: whatsapp`. Los reintentos
  y el respaldo a correo los agrega ST-52.
- T-09 solo tiene que agregar `CanalNotificacion.WHATSAPP: CanalWhatsApp` a `CLASES_CANAL`.

### 4. Cómo probarlo

```
docker compose run --rm api ruff check .
docker compose run --rm api python manage.py makemigrations --check --dry-run
docker compose run --rm api pytest notificaciones
```

La prueba `test_worker_manda_cada_notificacion_por_su_canal` mete una notificación de correo
y una de WhatsApp en el mismo lote: la de correo se envía y la de WhatsApp queda fallida.

### 5. Resultado

No hace falta migración. Todas las pruebas pasan.

**Responsable de la actividad:** David Melgoza (22420429) Katia Paola (22420438).
