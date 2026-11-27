# ST-189 - Endpoint para consultar la bitácora

## Objetivo

Que un administrador consulte los eventos de auditoría (HU-26). Los eventos los guarda `registrar_evento()` en la
tabla `EventoAuditoria` (ST-188); esta subtarea solo los expone, en modo lectura.

## Endpoint

`GET /api/v1/auditoria/` · permiso: `EsAdministrador` (más `IsAuthenticated` y `ContrasenaDefinitiva` de settings).

| Parámetro | Ejemplo | Qué hace |
| --- | --- | --- |
| `accion` | `?accion=login` | Acción exacta |
| `usuario` | `?usuario=<uuid>` | Eventos de esa persona. Si no es un UUID, `400 datos_invalidos` |
| `desde` | `?desde=2026-11-01` | Eventos de ese día en adelante (fecha `AAAA-MM-DD`, hora de `America/Mexico_City`) |
| `hasta` | `?hasta=2026-11-30` | Eventos hasta ese día, incluido |
| `page` | `?page=2` | Páginas de 20 en 20. El tamaño no se puede cambiar |

Los parámetros se combinan. Una fecha mal formada responde `400 datos_invalidos`. Si `desde` es posterior a `hasta`
la lista llega vacía (`200`), no es un error. Una página fuera de rango responde `404`.

Respuesta `200`:

```json
{
  "count": 25,
  "next": "http://…/api/v1/auditoria/?page=2",
  "previous": null,
  "results": [
    {
      "id": 31, "usuario": "…", "accion": "login", "resultado": "ok", "ip": "10.0.0.5",
      "user_agent": "Mozilla/5.0", "detalles": {}, "fecha": "2026-11-20T15:04:11Z"
    }
  ]
}
```

`usuario` es el id de la persona o `null` (login fallido o evento sin sesión).

## Errores

| Caso | Respuesta |
| --- | --- |
| Sin token | `401 no_autenticado` |
| Cliente u operativo | `403 sin_permiso` |
| Filtro mal formado | `400 datos_invalidos` |
| `POST`, `PUT`, `PATCH`, `DELETE` | `405 metodo_no_permitido` |

## Qué no hace

- No escribe: la bitácora solo se llena desde `registrar_evento()`; el endpoint es `GET` (y `HEAD`/`OPTIONS`).
- No cambia el modelo ni agrega migraciones.
- El filtro de fechas usa `fecha__date` y no aprovecha el índice `auditoria_fecha_idx`; si la tabla crece mucho,
  conviene pasar a rangos de fecha y hora.

## Reglas

| Regla | Dónde |
| --- | --- |
| Orden `-fecha`, `-id`: el `id` desempata fechas iguales y evita repetir o saltar eventos entre páginas | `AuditoriaView.queryset` |
| Filtros | `comun/filtros.py` |
| Campos de solo lectura | `comun/serializers.py` |

## Cómo comprobarlo

```bash
docker compose run --rm api pytest comun/tests/test_auditoria_endpoint.py -v
```

También se puede probar en `/api/docs/` (etiqueta `auditoria`) con un token de administrador.
