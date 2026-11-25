# ST-188 · registrar_evento() guarda en la tabla

**Historia:** HU-26 · Consultar la bitácora de auditoría
**Subtarea:** ST-188 · [Backend] Hacer que registrar_evento() guarde en EventoAuditoria

## Estado

Terminada. Lista para que la st-189 exponga la consulta.

## Qué es y para qué sirve

`registrar_evento()` era solo una línea en el log `svc.auditoria`. Ahora, además, crea una fila en `EventoAuditoria` (ST-187), así que la bitácora se puede consultar. La firma no cambió y nadie que la llama se tocó.

## Qué se hizo

- En `comun/eventos.py`:
  - `registrar_evento()` conserva el log y luego guarda el evento (usuario, acción, resultado, IP, user agent y detalles).
  - `limpiar_detalles()` ahora es recursiva.
  - `ip_de()` devuelve `None` si el valor no es una IP válida.
- Las pruebas en `comun/tests/test_registrar_evento_tabla.py`.

## Decisiones

- **Savepoint.** El guardado va en `transaction.atomic()` dentro de un `try/except`. Si la base falla, PostgreSQL deja rota solo esa parte y la transacción del llamador sigue usable. El error se registra con `logger.exception` y no se propaga.
- **Enmascarado recursivo.** Las claves sensibles (`password`, `codigo`, `token`…) valen `"***"` a cualquier profundidad, dentro de dicts, listas y tuplas. Nunca se guarda una contraseña, código o token.
- **IP inválida a `None`.** La columna es `inet`; un valor que no sea IP (por ejemplo, de un encabezado mal formado) haría fallar el guardado. Se guarda `None` y el evento no se pierde.
- **El log se conserva.** Sigue saliendo la misma línea JSON de antes.

## Qué no hace

- No cambia el modelo ni agrega migraciones.
- No expone endpoint: eso es la ST-189. Las pruebas de los flujos son la ST-190.
- Si el guardado falla, el evento queda solo en el log.
- Si la transacción del propio llamador hace rollback (por ejemplo `crear_admin` guarda su evento dentro de `transaction.atomic()`), la fila del evento se revierte con ella. El savepoint solo aísla fallos del guardado, no los rollbacks del llamador.

## Cómo comprobarlo

```bash
docker compose run --rm api ruff check .
docker compose run --rm api pytest comun/tests/test_registrar_evento_tabla.py comun/tests/test_eventos.py comun/tests/test_evento_auditoria.py -v
docker compose run --rm api pytest
```
