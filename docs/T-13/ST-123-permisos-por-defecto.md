# T-13 — Definir los roles y las clases de permiso

## ST-123. Configurar DEFAULT_PERMISSION_CLASSES

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se configuró `DEFAULT_PERMISSION_CLASSES` en `REST_FRAMEWORK` para que todo endpoint exija autenticación por defecto. Un endpoint público debe declarar `permission_classes = [AllowAny]` (T-13, criterio 3).

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `config/settings.py` | Nueva clave `DEFAULT_PERMISSION_CLASSES` con `IsAuthenticated`, dentro de `REST_FRAMEWORK` |
| `comun/tests/test_permisos_por_defecto.py` | 6 pruebas |

```python
    # t-13/st-123: todo endpoint exige autenticación salvo que declare AllowAny.
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
```

No se modificó ninguna otra configuración ni se creó ninguna migración.

### 3. Consideraciones

- Como `JWTAuthentication` es la primera clase de autenticación (t-04/st-21), una petición sin token responde `401` con código `no_autenticado`.
- Los endpoints públicos que ya existían siguen abiertos: `/api/v1/salud/` y `/api/v1/auth/registro/` declaran `AllowAny`, y `/api/schema/` y `/api/docs/` usan sus propios permisos de drf-spectacular.
- El backlog pide `IsAuthenticated + ContrasenaDefinitiva`. `ContrasenaDefinitiva` la crea y la agrega a esta misma lista la st-116 (HU-12), según su descripción.
- Cuando un `@action` declare `permission_classes`, debe usar `permisos_por_defecto_mas()` de `comun/permisos.py` (st-122) para no perder estos permisos.

### 4. Pruebas

```bash
docker compose run --rm api pytest comun/tests/test_permisos_por_defecto.py -v
```

| Prueba | Qué verifica |
|---|---|
| `test_settings_exige_autenticacion_por_defecto` | `IsAuthenticated` está en `DEFAULT_PERMISSION_CLASSES` |
| `test_vista_sin_permisos_declarados_responde_401_sin_token` | Una vista que no declara permisos responde 401 `no_autenticado` sin token |
| `test_salud_sigue_siendo_publica` | `/api/v1/salud/` responde 200 sin token |
| `test_registro_sigue_siendo_publico` | `/api/v1/auth/registro/` responde 400 (validación) y no 401 |
| `test_documentacion_de_la_api_sigue_siendo_publica` (2 casos) | `/api/schema/` y `/api/docs/` responden 200 sin token |

### 5. Resultado

Todo endpoint nuevo queda protegido por defecto, con 6 pruebas en verde.

**ST-123 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).
