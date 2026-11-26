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
   - Si el rol enviado es distinto al actual, se actualiza `usuario.rol` con `save(update_fields=["rol"])` sin incrementar `token_version`, de modo que `CustomTokenRefreshSerializer` refleje el nuevo rol en la siguiente renovación del token.
3. **`usuarios/urls_admin.py`:**
   - Se registró la ruta `<uuid:pk>/rol/` bajo el prefijo `/api/v1/usuarios/` (`name="usuario-rol"`).

## Contrato del endpoint

- **Método y ruta:** `PATCH /api/v1/usuarios/{id}/rol/`
- **Cuerpo esperado:**
  ```json
  {
    "rol": "operativo"
  }