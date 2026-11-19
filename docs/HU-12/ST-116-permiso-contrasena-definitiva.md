# HU-12 / ST-116 · Crear el permiso ContrasenaDefinitiva

**Subtarea:** ID 116 · [Backend] Crear el permiso ContrasenaDefinitiva
**Historia:** HU-12 · Cambiar la contraseña temporal en mi primer inicio de sesión
**Responsable:** Isamar Chávez Díaz (chamar29) · **Revisa:** Isis Vázquez (isis0015)
**Estado:** En revisión

## Descripción

Cuando el administrador crea una cuenta operativa con una contraseña temporal, el usuario tiene
`debe_cambiar_password = True`. El login (HU-05, ST-81) copia ese valor al token como claim.
El permiso `ContrasenaDefinitiva` **lee ese claim** y, mientras sea `True`, cualquier endpoint
responde **403** con el código `debe_cambiar_password`. Así el usuario solo puede cambiar su
contraseña.

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `comun/permisos.py` | Clase `ContrasenaDefinitiva` (bloque marcado `# t-12/st-116`) |
| `config/settings.py` | Se agrega a `DEFAULT_PERMISSION_CLASSES`, después de `IsAuthenticated` |
| `comun/tests/test_contrasena_definitiva.py` | 7 pruebas |

```python
class ContrasenaDefinitiva(BasePermission):
    message = "Debes cambiar tu contraseña temporal antes de continuar."
    code = "debe_cambiar_password"

    def has_permission(self, request, view):
        return _claim(request, "debe_cambiar_password") is not True
```

Respuesta cuando bloquea:

```json
{"codigo": "debe_cambiar_password", "mensaje": "Debes cambiar tu contraseña temporal antes de continuar.", "campos": {}}
```

## Cómo usarlo en otros endpoints

- **No hay que hacer nada:** al estar en `DEFAULT_PERMISSION_CLASSES`, aplica a todos los endpoints.
- **Si un endpoint declara sus propios permisos**, usa `permisos_por_defecto_mas(...)` para no
  perderlo: `permission_classes = permisos_por_defecto_mas(EsAdministrador)`.
- **El endpoint de cambiar contraseña (HU-11)** debe seguir funcionando con la contraseña
  temporal, así que declara `permission_classes = [IsAuthenticated]` (sin este permiso).
- Los endpoints públicos (`AllowAny`: login, registro, salud) no se ven afectados.

## Decisiones

- **`message` y `code` en lugar de importar `DebeCambiarPassword`:** `comun/errores.py` importa
  `rest_framework.views`, que a su vez carga `DEFAULT_PERMISSION_CLASSES`. Importarla desde
  `comun/permisos.py` causa una importación circular al arrancar. DRF arma la misma respuesta
  con `message` y `code` del permiso.
- **Sin token, el permiso deja pasar:** así `IsAuthenticated` sigue respondiendo 401, no 403.

## Pruebas

| Prueba | Esperado |
| --- | --- |
| `test_esta_en_los_permisos_por_defecto` | Está en `DEFAULT_PERMISSION_CLASSES` después de `IsAuthenticated` |
| `test_con_contrasena_temporal_responde_403` | 403 `debe_cambiar_password` |
| `test_con_contrasena_definitiva_deja_pasar` | 200 |
| `test_token_sin_el_claim_deja_pasar` | 200 |
| `test_sin_token_sigue_respondiendo_401` | 401 `no_autenticado` |
| `test_cambiar_password_funciona_con_contrasena_temporal` | 200 con `[IsAuthenticated]` |
| `test_permisos_por_defecto_mas_incluye_contrasena_definitiva` | El helper lo incluye |

```powershell
docker compose run --rm api pytest comun/tests/test_contrasena_definitiva.py -v
```

Resultado: 7 pruebas en verde; el resto del proyecto sigue pasando.

## Depende de

- **ST-81 (Danna, PR #38):** que el login agregue el claim `debe_cambiar_password`. Las pruebas
  lo ponen a mano mientras tanto.
- **ST-117 (Isis):** al cambiar la contraseña, el campo pasa a `False` y se emiten tokens nuevos.