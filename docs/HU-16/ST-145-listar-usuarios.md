# ST-145 - Endpoint para listar, buscar y filtrar usuarios

## Objetivo

Que un administrador consulte las cuentas y encuentre una rápido, sin revisarlas una por una (HU-16).
Esta subtarea agrega el `GET` a la ruta que ya tenía el `POST` de alta (ST-140). Los índices son ST-146 y las pruebas
generales de la historia, ST-147.

## Endpoint

`GET /api/v1/usuarios/` · permiso: `EsAdministrador` (más `IsAuthenticated` y `ContrasenaDefinitiva` de settings).

| Parámetro | Ejemplo | Qué hace |
| --- | --- | --- |
| `search` | `?search=ana blanco` | Busca en nombre, apellidos, correo y teléfono, sin importar mayúsculas. Cada palabra debe aparecer en alguno de esos campos |
| `rol` | `?rol=operativo` | `administrador`, `cliente` u `operativo` |
| `estado` | `?estado=activo` | `pendiente`, `activo` o `inactivo` |
| `page` | `?page=2` | Páginas de 20 en 20. El tamaño no se puede cambiar |

Los parámetros se combinan: `?search=blanco&rol=operativo&page=1`. Un `rol` o `estado` inexistente responde
`400 datos_invalidos`; un valor vacío se ignora.

Respuesta `200`:

```json
{
  "count": 25,
  "next": "http://…/api/v1/usuarios/?page=2",
  "previous": null,
  "results": [
    {
      "id": "…", "nombre": "Ana", "apellidos": "Blanco", "correo": "ana.blanco@ejemplo.com",
      "telefono": "+524431110001", "rol": "operativo", "estado": "activo",
      "bloqueada": false, "ultimo_acceso": "2026-11-20T15:04:11Z"
    }
  ]
}
```

`ultimo_acceso` es `null` si la persona nunca ha iniciado sesión. La respuesta no incluye contraseña, `token_version`
ni datos de 2FA. Una página fuera de rango responde `404`.

## Reglas

| Regla | Dónde |
| --- | --- |
| Sin token `401`; cliente u operativo `403 sin_permiso`; administrador con contraseña temporal `403 debe_cambiar_password` | `UsuariosView.permission_classes` |
| Orden fijo por nombre, apellidos y correo; sin él, las páginas podrían repetir o saltarse usuarios | `UsuariosView.get_queryset` |
| `rol` y `estado` salen de los `choices` del modelo | `usuarios/filtros.py` |
| Páginas de 20; reutilizable por otros listados | `comun/paginacion.py` |
| `bloqueada` se calcula en la misma consulta del listado (sin una consulta por usuario) | `usuarios/bloqueos.py` |

## Cómo se calcula `bloqueada`

Una cuenta está bloqueada si django-axes tiene un intento con al menos `AXES_FAILURE_LIMIT` fallos (5) dentro del
`AXES_COOLOFF_TIME` (15 minutos). El intento se asocia a la cuenta por su `username`: el correo (sin importar
mayúsculas) o el teléfono en formato E.164.

> **Limitación conocida, fuera de esta subtarea (HU-25).** Hoy Axes guarda `username = None` en los logins reales:
> `AXES_USERNAME_FORM_FIELD` vale `email` (el `USERNAME_FIELD` del modelo) pero `usuarios/tokens.py` autentica con
> `username=`, así que Axes no encuentra el dato. Consecuencias:
>
> - `bloqueada` aparecerá siempre en `false` hasta que se corrija.
> - El bloqueo actual es **por IP, no por cuenta**: cinco fallos desde una IP bloquean a cualquier cuenta que se intente
>   desde esa IP, y los fallos contra cuentas distintas se suman.
>
> `test_tras_cinco_logins_fallidos_reales_la_cuenta_aparece_bloqueada` documenta el problema con un `xfail` estricto:
> cuando se corrija HU-25 pasará y habrá que quitarle la marca.

## Búsqueda: qué esperar

- Es de tipo "contiene" (`icontains`: el texto puede estar en cualquier parte del campo). Los índices de correo y teléfono no la aceleran; para pocos miles de
  usuarios no importa, y de crecer habría que usar un índice `pg_trgm` (ST-146).
- En PostgreSQL no ignora acentos: `ramirez` no encuentra a `Ramírez`. Para ignorarlos haría falta la extensión
  `unaccent`.
- El teléfono se guarda en E.164 (`+524431234567`), así que `443 123` no coincide; sí coincide `443` o `+52443`.

## Archivos

| Archivo | Cambio |
| --- | --- |
| `usuarios/views_admin.py` | `AltaUsuarioView` pasa a `UsuariosView` con `GET` (listado) y `POST` (alta, sin cambios) |
| `usuarios/serializers_admin.py` | `UsuarioListaSerializer` |
| `usuarios/filtros.py` | `UsuarioFilter` (`rol`, `estado`) |
| `usuarios/bloqueos.py` | `con_bloqueada()` |
| `comun/paginacion.py` | `PaginacionDe20` |
| `usuarios/urls_admin.py`, `config/settings.py`, `requirements.txt` | Ruta, `django_filters` en `INSTALLED_APPS` y `django-filter==26.2` |
| `usuarios/tests/test_listar_usuarios.py` | 44 pruebas y 1 `xfail` |
| `docs/HU-15/ST-140-alta-usuario-operativo.md` | Nombre de la vista actualizado |

## Pendiente en otras subtareas

- **ST-146:** índices. El correo (`Lower(email)`) y el teléfono ya tienen índices únicos; falta decidir si hace falta
  `pg_trgm` para la búsqueda por "contiene".
- **ST-147:** pruebas generales de HU-16 (esta subtarea ya trae las suyas).
- **HU-17:** si el detalle reutiliza `UsuarioListaSerializer`, su queryset debe anotar `bloqueada` con
  `con_bloqueada()`; de lo contrario el serializer fallará.
- **HU-25:** corregir el `username` que guarda Axes.
