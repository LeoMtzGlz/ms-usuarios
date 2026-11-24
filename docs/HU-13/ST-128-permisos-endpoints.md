# ST-128 - Permisos aplicados a los endpoints disponibles

## Objetivo

Aplicar `permission_classes` de acuerdo con la matriz de ST-127 sin crear rutas que todavía pertenecen a otras
subtareas.

## Resultado

| Endpoint disponible | Permiso aplicado | Ubicación |
| --- | --- | --- |
| `GET /api/v1/salud/` | `AllowAny` | `comun/views.py` |
| `POST /api/v1/auth/registro/` | `AllowAny` | `usuarios/views.py` |
| `GET /api/schema/` | `AllowAny` | `config/urls.py` |
| `GET /api/docs/` | `AllowAny` | `config/urls.py` |
| `/admin/` | Control de Django mediante `is_staff` | `config/urls.py` |

Salud y registro desactivan la autenticación porque forman parte del flujo previo a la sesión. El esquema y la
interfaz Swagger permiten el acceso anónimo con `AllowAny`, pero conservan la autenticación JWT: si una petición
envía un token inválido, responde `401` con el formato de errores del equipo.

## Endpoints planeados

Las rutas marcadas como **Planeado**, **En rama** o **En PR** en ST-127 no se modifican aquí porque todavía no
forman parte de `development`. Cuando cada implementación se integre deberá declarar el permiso indicado en la
matriz. ST-129 comprobará las combinaciones de acceso sobre los endpoints que estén disponibles.

## Verificación

- Todos los endpoints existentes fueron revisados.
- Los recursos públicos declaran `AllowAny` de forma explícita.
- Ninguna ruta protegida se convirtió en pública.
- No se inventaron rutas ni vistas que correspondan a otras subtareas.
