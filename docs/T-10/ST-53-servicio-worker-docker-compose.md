# T-10 — Procesar la bandeja de salida con reintentos y respaldo de canal

## ST-53. Servicio worker en Docker Compose

**Estado:** En revisión  
**Revisa:** Santiago Mora (santiago-amn)

### 1. Descripción

Se agregó el servicio `worker` al `docker-compose.yml`: corre `python manage.py procesar_notificaciones`
(ST-51, con los reintentos y el respaldo de ST-52) como un contenedor propio, para que la bandeja de salida
se vacíe sin abrir una terminal.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `docker-compose.yml` | Servicio `worker`: misma imagen (`build: .`), mismo `.env` y mismo montaje de código que `api`; `command` propio; `depends_on` de `db` con `service_healthy`; `restart: unless-stopped`; sin puertos |
| `README.md` | Línea en la tabla de comandos frecuentes |

No se tocan `db`, `api`, el código Python ni las migraciones.

### 3. Cómo usarlo

```bash
docker compose up -d worker      # levantarlo (también levanta db)
docker compose logs -f worker    # debe decir «Worker de notificaciones iniciado»
docker compose stop worker       # SIGTERM: termina el lote en curso y sale con código 0
docker compose up -d --scale worker=2   # dos workers a la vez
```

No publica puertos (el 5433 ya es de `db`), por lo que se puede escalar sin choques.

### 4. Las migraciones: lo que se observó

El `CMD` del `Dockerfile` ejecuta `migrate` y luego `runserver`; eso lo hace `api`. El `worker` cambia el
comando, así que **no migra**. Decidimos no hacerlo migrar para no competir con el `migrate` de `api`.

Con una base nueva (`docker compose down -v` y luego `docker compose up -d worker`, sin `api`) el worker
falla con `relation "notificaciones_notificacion" does not exist` y, por `restart: unless-stopped`, queda
reiniciándose. Al levantar `api` (que migra), el worker se recuperó solo en unos segundos y escribió
«Worker de notificaciones iniciado». Por eso:

- Con una base nueva, levantar `api` primero (o `docker compose up -d`, que levanta ambos): el worker puede
  reiniciarse unas veces hasta que `api` termine de migrar, y luego queda estable.
- Con una base ya migrada, el worker arranca a la primera.

No se añadió `depends_on: api`: `api` no tiene healthcheck, y `service_started` no garantiza que el `migrate`
haya terminado, así que no resolvería nada.

### 5. Verificación

| Prueba | Resultado |
|---|---|
| `docker compose config -q` | Sin errores |
| `up -d worker` en base ya migrada / tras migrar `api` | Log «Worker de notificaciones iniciado (cada 5s, lotes de 20)» |
| `up -d --scale worker=2` | Dos contenedores `worker` en ejecución, cada uno con su mensaje de inicio |
| `docker compose stop worker` | Terminó en unos 3 s; ambos contenedores `Exited (0)` |
| `docker compose run --rm api pytest notificaciones -q` y `ruff check .` | Ver el resultado en el reporte de la tarea |

Dos workers son seguros por el `select_for_update(skip_locked=True)` de ST-51.
