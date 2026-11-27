# ST-131 · Crear el endpoint de cambio de rol

- **Historia de usuario:** HU-14 · Cambiar el rol de un usuario
- **Rama:** `t-14/st-131`
- **Responsable:** Daniel Orlando Ceja Olloqui (`l22420448@jiquilpan.tecnm.mx`)

## Objetivo

Exponer el endpoint `PATCH /api/v1/usuarios/{id}/rol/` exclusivo para administradores, permitiendo asignar un rol válido (`administrador`, `cliente` u `operativo`) a otra cuenta e impidiendo que un administrador cambie o quite su propio rol.

## Cambios realizados

1. **`usuarios/serializers_admin.py`:**
   - Se agregó `CambioRolSerializer` con validación de `rol` contra `Rol.choices`.
2. **`usuarios/views_admin.py`:**
   - Se implementó `CambiarRolView` (`PATCH`) protegido con `permisos_por_defecto_mas(EsAdministrador)`.
   - Se valida que `usuario.pk != request.user.pk`; si un administrador intenta modificar su propio rol se responde `400 Bad Request`.
   - Si el rol enviado es distinto al actual, se actualiza `usuario.rol` y se incrementa `usuario.token_version` (`save(update_fields=["rol", "token_version"])`) para revocar de inmediato la sesión vigente y evitar que un administrador degradado conserve privilegios durante la vida restante de su token.
3. **`usuarios/urls_admin.py`:**
   - Se registró la ruta `<uuid:pk>/rol/` bajo el prefijo `/api/v1/usuarios/` (`name="usuario-rol"`).
4. **`usuarios/tests/test_autorizacion_endpoints.py`:**
   - Se clasificó `("patch", "/api/v1/usuarios/<uuid>/rol/")` dentro de `RUTAS_PROTEGIDAS`.

## Contrato del endpoint

- **Método y ruta:** `PATCH /api/v1/usuarios/{id}/rol/`
- **Cuerpo esperado:**

```json
{
  "rol": "operativo"
}
```

- **Respuestas:**
  - `200 OK`: `{"id": "<uuid>", "rol": "operativo"}`
  - `400 Bad Request`: rol inválido o intento de cambiar el propio rol.
  - `401 Unauthorized`: token ausente o inválido.
  - `403 Forbidden`: usuario autenticado sin rol `administrador`.
  - `404 Not Found`: usuario destino inexistente.

## Verificación

- `ruff check .` sin advertencias ni errores.
- `pytest` ejecutado sobre toda la suite sin regresiones.