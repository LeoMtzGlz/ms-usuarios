# HU-12 — Cambiar la contraseña temporal en mi primer inicio de sesión

## ST-117 : [Backend] Marcar la contraseña como definitiva al cambiarla

**Estado:** En revisión.

**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)

**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-118

### Descripción
Cuando un usuario operativo cambia la contraseña temporal que le dio el administrador, el campo `debe_cambiar_password` debe pasar a `False`. Así la API deja de exigirle el cambio.

### Resultado
Método nuevo `Usuario.cambiar_password(nueva, request=None)` en `usuarios/models.py`. Sigue el mismo patrón que `cambiar_estado()`: es el único lugar del código que cambia la contraseña de un usuario ya registrado.

En un solo guardado:

| Qué hace | Por qué |
| --- | --- |
| `set_password(nueva)` | Guarda la contraseña nueva con hash (Argon2) |
| `debe_cambiar_password = False` | La contraseña ya es definitiva (criterio de HU-12) |
| `token_version += 1` | Cierra las sesiones abiertas con la contraseña anterior |
| `registrar_evento("password_cambiado", ...)` | Deja rastro en la bitácora con `era_temporal`, nunca con la contraseña |

Solo guarda `password`, `debe_cambiar_password` y `token_version` (`update_fields`), para no pisar cambios de otros campos.

### Lo que **no** hace (a propósito)
- **No valida la política de contraseñas.** Lo hace el serializer del endpoint de HU-11 con `validate_password()` antes de llamar al método.
- **No emite tokens.** Después de llamarlo, el endpoint de HU-11 debe devolver tokens nuevos (segundo criterio de HU-12).

### Cómo usarlo desde el endpoint de HU-11

```python
# usuarios/views.py (HU-11): después de validar la contraseña actual y la nueva
usuario = request.user
usuario.cambiar_password(serializer.validated_data["password_nueva"], request=request)

refresh = RefreshToken.for_user(usuario)
return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
```

> **Coordinación:** el endpoint de HU-11 todavía no existe. Quien lo haga debe usar `cambiar_password()` en lugar de llamar a `set_password()` directamente; si no, `debe_cambiar_password` se queda en `True` y el usuario sigue bloqueado.

### Pruebas
`usuarios/tests/test_cambiar_password.py`:

```bash
docker compose exec api pytest usuarios/tests/test_cambiar_password.py -v
```