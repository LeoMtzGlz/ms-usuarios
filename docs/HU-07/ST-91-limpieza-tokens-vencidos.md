# HU-07 / ST-91 · Programar la limpieza de tokens vencidos

**Subtarea:** ID 91 · [Configuración] Programar la limpieza de tokens vencidos
**Historia:** HU-07 · Renovar mi sesión sin volver a iniciar sesión
**Responsable:** Maritza Santibañez (l22420423)
**Rama:** `t-07/st-91` · **Depende de:** ST-89 (lista negra de SimpleJWT) y ST-169 (`ControlLimpieza`)
**Estado:** En revisión

## Descripción

El backlog pide correr `manage.py flushexpiredtokens` **en el worker una vez al día**. Se siguió
el mismo patrón de la ST-169: el worker `procesar_notificaciones` da una vuelta cada 5 segundos
y en cada vuelta llama a `limpiar_tokens_si_toca()`, que solo limpia si ya pasaron 24 horas.

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `usuarios/limpieza.py` | `limpiar_tokens_si_toca()` (bloque `# t-07/st-91`) |
| `notificaciones/management/commands/procesar_notificaciones.py` | El worker llama a `_limpiar_tokens()` en cada vuelta (líneas `# t-07/st-91`) |
| `usuarios/tests/test_limpieza_tokens.py` | 5 pruebas |

No hay migración: se reusa la tabla `ControlLimpieza` de la ST-169 con otra fila
(`nombre = "limpiar_tokens"`). No se tocó `docker-compose.yml` ni `.env.example`.

## Cómo funciona

1. `limpiar_tokens_si_toca()` busca la fila `limpiar_tokens` en `ControlLimpieza`:
   - si la última limpieza fue hace **menos de 24 h**, no hace nada;
   - si ya pasaron 24 h (o nunca se ha hecho), corre `flushexpiredtokens` y guarda la hora.
2. `flushexpiredtokens` (SimpleJWT) borra los `OutstandingToken` vencidos y, en cascada, sus
   `BlacklistedToken`. Los tokens vigentes no se tocan.
3. **Varios workers:** la fila se bloquea con `select_for_update(skip_locked=True)`; solo uno limpia.
4. Si la limpieza falla, el worker **solo lo anota en el log y sigue enviando notificaciones**.

## Cómo probarlo

```bash
docker compose up -d
docker compose exec api python -m pytest usuarios/tests/test_limpieza_tokens.py -v
docker compose exec api python manage.py flushexpiredtokens   # limpieza a mano
docker compose logs --tail=20 worker                          # "Limpieza de tokens vencidos completada"
```

## Pruebas

| Prueba | Resultado |
| --- | --- |
| Borra tokens vencidos y su lista negra; conserva los vigentes | ✅ |
| Dos veces el mismo día: solo limpia la primera | ✅ |
| Pasadas 24 h vuelve a limpiar y guarda la hora | ✅ |
| El worker (`procesar_notificaciones --una-vez`) limpia | ✅ |
| Si la limpieza falla, el worker sigue | ✅ |

Resultado: `5 passed`. Suite completa: `794 passed, 2 xfailed`.

## Checklist

- [x] `ruff check .` sin errores
- [x] `makemigrations --check` sin cambios
- [x] `docker compose config` válido con el `.env` del repo
