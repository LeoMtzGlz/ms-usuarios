# ST-187 · Modelo EventoAuditoria

**Historia:** HU-26 · Consultar la bitácora de auditoría
**Subtarea:** ST-187 · [Backend] Crear el modelo EventoAuditoria
**Autor:** David Melgoza (l22420429) · **Revisor:** Santiago Mora (santiago-amn)

## Estado

Terminada. Lista para que la st-188 guarde los eventos en la tabla.

## Qué es y para qué sirve

La bitácora de auditoría deja constancia de quién hizo qué, cuándo y desde dónde: logins, logouts, registros, cambios de rol, envíos fallidos, etc. Hasta ahora `registrar_evento()` (T-03) solo escribía una línea en el log `svc.auditoria`. Este modelo es la tabla donde se van a guardar esos eventos para que un administrador pueda consultarlos.

## Qué se hizo

- En `comun/models.py`: la lista `ResultadoEvento` y el modelo `EventoAuditoria`.
- La migración `comun/migrations/0001_inicial_evento_auditoria.py`. Es la primera de la app `comun`, así que no choca con la numeración de `usuarios` ni de `notificaciones`.
- Las pruebas en `comun/tests/test_evento_auditoria.py`.

No se tocaron archivos compartidos (`config/settings.py`, `requirements.txt`, `.env.example`, `urls.py`): `comun` ya estaba en `INSTALLED_APPS`.

## Campos

| Campo | Tipo | Para qué sirve |
| --- | --- | --- |
| `usuario` | Clave foránea a `Usuario`, puede ir vacía | Quién hizo la acción. Vacío en un login fallido o en un evento sin sesión |
| `accion` | Texto de hasta 50 caracteres | Qué pasó: `login`, `logout`, `rol_cambiado`… (catálogo en la nota de HU-26 de la st-188) |
| `resultado` | Texto (`ResultadoEvento`) | `ok` (por defecto) o `error` |
| `ip` | Dirección IP (`inet`), puede ir vacía | Desde dónde. Acepta IPv4 e IPv6 |
| `user_agent` | Texto sin límite, puede ir vacío | Navegador o app que hizo la petición |
| `detalles` | JSONField (`jsonb` en PostgreSQL), `{}` por defecto | Datos extra del evento, ya enmascarados |
| `fecha` | Fecha y hora | Se llena sola al crear el evento |

## Decisiones

- **Va en la app `comun`.** Ahí vive `registrar_evento()`, que es quien va a escribir en la tabla, y su `models.py` estaba vacío.
- **Sigue el contrato de la st-188.** Los campos, sus nombres y el `SET_NULL` son los que Santiago propuso en su nota de HU-26, para que su subtarea encaje sin cambios.
- **`on_delete=SET_NULL`.** Si se borra a la persona, sus eventos se quedan con `usuario` vacío. Así no se pierde el historial.
- **Índice por fecha** (`auditoria_fecha_idx`), como pide el backlog. Sirve para el orden y para filtrar por rango de fechas.
- **Índice por acción y fecha** (`auditoria_accion_fecha_idx`). La st-189 filtra por acción y fechas; este índice hace rápida esa consulta. El filtro por usuario ya tiene el índice que Django crea para toda clave foránea.
- **Orden por defecto: el más reciente primero** (`-fecha`). Es como se lee una bitácora.
- **`detalles` con `DjangoJSONEncoder`.** Si alguien manda un UUID, una fecha o un Decimal en los detalles, se guarda como texto en lugar de tronar.
- **`accion` sin lista fija de opciones.** Cada historia agrega su acción; una lista cerrada obligaría a cambiar el modelo y hacer una migración cada vez.
- **`user_agent` como texto sin límite.** Algunos user agents pasan de 255 caracteres; así la st-188 no tiene que recortarlos.

## Para la st-188 (cómo usarlo)

```python
from comun.models import EventoAuditoria, ResultadoEvento

EventoAuditoria.objects.create(
    usuario=usuario,               # o None
    accion=accion,
    resultado=resultado,           # "ok" o "error"
    ip=ip_de(request),             # o None
    user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    detalles=limpiar_detalles(detalles),
)
```

- El modelo no importa nada de `usuarios`, así que se puede importar al inicio de `comun/eventos.py` sin import circular. Se probó con `manage.py check` y las pruebas de `usuarios`.
- `ip` es de tipo `inet` en PostgreSQL: un valor que no sea IP hace fallar el guardado con `ValueError`. Si se toma de un encabezado que puede venir mal, conviene pasar `None`.
- Para que un fallo al guardar no rompa el flujo que llamó, el `create` debe ir dentro de `transaction.atomic()`. Si el error ocurre ya en la base de datos, sin ese bloque PostgreSQL deja la transacción rota y las consultas siguientes del mismo request también fallan.

## Qué no hace

Este modelo solo guarda datos. Lo demás de HU-26 queda en otras subtareas (las tres de l22420391):

- ST-188: que `registrar_evento()` guarde en esta tabla.
- ST-189: el endpoint `GET /api/v1/auditoria/` (filtros, paginación, solo administrador, sin edición ni borrado).
- ST-190: las pruebas de los flujos.

## Cómo comprobarlo

```bash
docker compose run --rm api ruff check .
docker compose run --rm api python manage.py makemigrations --check --dry-run
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest comun/tests/test_evento_auditoria.py -v
docker compose run --rm api pytest
```

Las 9 pruebas nuevas revisan:

- Los valores por defecto de un evento mínimo.
- Que se guardan todos los campos, con IPv6.
- Que `detalles` es `jsonb` y se puede filtrar por sus claves.
- Que acepta UUID y fechas en `detalles`.
- Que existen el índice por fecha y el de acción y fecha.
- Que borrar al usuario conserva su historial.
- Que el más reciente sale primero y se puede filtrar por fechas.
- Que los `detalles` por defecto no se comparten entre eventos.
- Cómo se muestra un evento sin guardar.
