# HU-08 — Cerrar sesión

## ST-94. Crear el endpoint de logout

**Estado:** En revisión

**Responsable:** Claudia Maritza Santibáñez García (l22420423)

### 1. Descripción

Se implementó el endpoint de cierre de sesión. Revoca el refresh token que envía el cliente agregándolo a la lista negra de SimpleJWT (ST-89), para que ya no pueda renovar la sesión en ese dispositivo.

### 2. Archivos modificados

| Archivo | Cambio |
|---|---|
| `usuarios/tokens.py` | `LogoutSerializer`: valida el refresh, verifica el dueño y lo revoca |
| `usuarios/views.py` | `LogoutView` con `IsAuthenticated` |
| `usuarios/urls.py` | Registro de la ruta `logout/` |
| `usuarios/tests/test_logout.py` | Pruebas del endpoint |
| `usuarios/tests/test_autorizacion_endpoints.py` | La ruta se agrega a `RUTAS_PROTEGIDAS` |

### 3. Endpoint

**Método:** `POST`

**Ruta:** `/api/v1/auth/logout/`

**Autenticación:** `Authorization: Bearer <access_token>`

Solicitud:

```json
{
    "refresh": "<refresh_token>"
}
```

Respuesta exitosa (`200`):

```json
{
    "mensaje": "Sesión cerrada correctamente."
}
```

### 4. Reglas

- Requiere un access válido. Sin él responde `401 no_autenticado`.
- El refresh debe pertenecer al usuario del access. Si es de otro usuario responde `403 sin_permiso` y no se revoca.
- Si el refresh ya estaba en la lista negra responde `200`: cerrar sesión dos veces no da error.
- Un refresh malformado, vencido o un access enviado como refresh responden `401 token_invalido`.
- Sin el campo `refresh` responde `400 datos_invalidos`.
- Solo exige `IsAuthenticated` (no `ContrasenaDefinitiva`), así que un usuario con contraseña temporal también puede cerrar sesión.
- Los access ya emitidos siguen siendo válidos hasta que vencen (15 minutos).

### 5. Criterios de aceptación de HU-08

| Criterio | Cobertura |
|---|---|
| `POST /api/v1/auth/logout/` manda el refresh a la lista negra | `test_logout_invalida_refresh_token` |
| Un refresh de otro usuario responde 403 | `test_logout_rechaza_refresh_de_otro_usuario` |
| Cerrar sesión dos veces no da error | `test_logout_dos_veces_no_falla` |
| El cierre queda en la bitácora | Fuera de alcance: lo cubre ST-95 |

### 6. Pruebas realizadas

```bash
python -m pytest usuarios/tests/test_logout.py usuarios/tests/test_autorizacion_endpoints.py -q
python -m pytest -q
ruff check .
python manage.py makemigrations --check --dry-run
git diff --check
```
