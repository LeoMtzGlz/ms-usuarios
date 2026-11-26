# HU-18 — Desactivar o reactivar una cuenta

## ST-154. Pruebas

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Pruebas de punta a punta de la HU-18: **inactivo no entra; su refresh no renueva; reactivado entra.**

La cuenta se desactiva y se reactiva con los endpoints reales de st-153 (`POST /api/v1/usuarios/{id}/desactivar/` y `/reactivar/`), y después se prueba el login (`/api/v1/auth/login/`), la renovación (`/api/v1/auth/token/renovar/`) y un endpoint protegido (`/api/v1/auth/accesos/`).

Depende de st-153 (endpoints), st-90 (renovación que valida estado y `token_version`) y st-167 (historial de accesos), ya integradas en `development`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_pruebas_hu18.py` | Nuevo: 8 pruebas |

No se modificó código de la aplicación, ningún modelo ni se creó ninguna migración.

### 3. Casos probados

| Grupo | Prueba | Resultado esperado |
|---|---|---|
| Inactivo no entra | `test_el_login_responde_cuenta_inactiva` | `403 cuenta_inactiva`, sin `access` ni `refresh` |
| | `test_el_intento_queda_registrado_como_fallido` | El historial guarda el intento con `exitoso=False` |
| | `test_su_access_anterior_ya_no_sirve` | El access que tenía antes de desactivarlo responde `401` |
| Su refresh no renueva | `test_su_refresh_ya_no_renueva` | `401 token_invalido`, sin tokens nuevos |
| | `test_el_refresh_anterior_sigue_rechazado_despues_de_reactivar` | Reactivar no revive los tokens viejos: `401 token_invalido` |
| Reactivado entra | `test_el_login_entrega_los_tokens` | `200` con `access`, `refresh` y su `id` |
| | `test_su_access_nuevo_si_sirve` | El endpoint protegido responde `200` |
| | `test_su_refresh_nuevo_si_renueva` | `200` con `access` y `refresh` nuevos |

### 4. Pruebas

```bash
docker compose run --rm api pytest usuarios/tests/test_pruebas_hu18.py -v
```

Resultado: **8 passed**.

### 5. Resultado

Se comprobó que una cuenta desactivada no puede iniciar sesión ni seguir usando sus tokens, que al reactivarla los tokens anteriores siguen sin servir y que puede volver a entrar con un login nuevo.
