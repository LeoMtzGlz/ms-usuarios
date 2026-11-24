# HU-26 · Diseño de la bitácora de auditoría (ST-188, ST-189, ST-190)

**Historia:** HU-26 · Consultar la bitácora de auditoría
**Responsable:** Santiago Mora (santiago-amn)
**Estado:** aprobado el 2026-11-22. Cubre las tres subtareas; cada una tiene su propio documento en su carpeta.

## Para qué

Hoy `registrar_evento()` solo escribe una línea en el log `svc.auditoria`. Un administrador no puede consultar quién hizo qué, cuándo y desde dónde. Esta historia guarda cada evento en la tabla `EventoAuditoria` (modelo de la ST-187, ya en `development`) y la expone en un endpoint de solo lectura.

## Objetivos

- **ST-188:** `registrar_evento()` guarda el evento en la tabla, sin cambiar su firma.
- **ST-189:** `GET /api/v1/auditoria/` con filtros por acción, usuario y fechas, paginado y solo para administradores.
- **ST-190:** pruebas de que cada flujo existente crea su evento, de que un no administrador recibe 403 y de que ningún evento contiene contraseñas.

## Fuera de alcance

- Agregar llamadas a `registrar_evento()` en flujos de otras historias (login, logout, recuperación, bloqueo). Cada historia agrega la suya; sus PRs siguen abiertas.
- Editar o borrar eventos por la API.
- Cambiar el modelo de la ST-187.

## Qué sería un fracaso aunque funcione

- Que un fallo al guardar el evento rompa el flujo que lo llamó (registro, alta, cambio de contraseña…).
- Que se guarde una contraseña, un código o un token en `detalles`.
- Que haya que tocar a quienes ya llaman a `registrar_evento()`.

## Restricciones

- La firma `registrar_evento(accion, usuario=None, request=None, resultado="ok", **detalles)` no cambia.
- Los errores de acceso usan el catálogo (`docs/catalogo-errores.md`).
- `ip` es `inet` en PostgreSQL: un valor inválido hace fallar el guardado, así que se descarta antes de guardar.

## Enfoques considerados

| Enfoque | Qué cambia | Por qué sí o no |
| --- | --- | --- |
| **A. Guardar en el momento, dentro de `transaction.atomic()` y con `try/except`** | La fila se crea al llamar; si falla, se deja el error en el log y se sigue | **Elegido.** Un fallo no rompe el flujo ni deja rota la transacción del request (ver nota de la ST-187). Sin piezas nuevas |
| B. Guardar con `transaction.on_commit()` | La fila se crea al terminar la transacción | Pierde el evento si el flujo hace rollback justo cuando importa (por ejemplo un intento fallido) |
| C. Cola o worker asíncrono | El evento viaja por una cola | Agrega infraestructura que nadie pidió |

## Decisiones

- **Nombres de acción: se conservan los que ya usa el código** (`registro`, `alta_usuario`, `password_cambiado`, `estado_cambiado`, `privacidad_aceptada`, `2fa_*`, `admin_creado`). La nota inicial de HU-26 proponía otros (`usuario_creado`, `contrasena_cambiada`); no se usan para no renombrar lo que ya existe. Esto es decisión mía, no acordada con el equipo.
- **Endpoint:** mismo patrón que `UsuariosView` (HU-16): `EsAdministrador`, `PaginacionDe20`, `DjangoFilterBackend`. Solo `GET`; los demás métodos responden 405.
- **Filtros:** `accion` (exacta), `usuario` (id), `desde` y `hasta` (rango sobre `fecha`). Más reciente primero, como ya ordena el modelo.
- **ST-190 cubre solo lo que existe hoy.** Los flujos pendientes de otras historias quedan listados en el documento de la 190 para que quien los implemente los agregue.

## Lo que queda al implementador

- El nombre exacto de la clase del filtro y del serializador.
- El texto de los mensajes de log cuando falle el guardado.
- La forma de cada prueba, mientras cubra lo listado en la ST-190.
