# HU-09 — Cerrar sesión en todos los dispositivos

## ST-99. Pruebas de logout-todo

**Estado:** Completada  
**Responsable:** Bryan Gael Esquivel Pérez (l22420415)

### 1. Descripción

Se agregaron las pruebas automáticas de `POST /api/v1/auth/logout-todo/` (ST-98). Simulan dos dispositivos del mismo usuario, cada uno con su propio login, y comprueban lo que pide el backlog: *"El refresh de otro dispositivo deja de renovar"*.

No se modificó código de la aplicación: solo se agregan pruebas.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_logout_todo.py` | Pruebas de logout-todo con dos dispositivos, `token_version`, bitácora y casos de error |

### 3. Qué cubre cada prueba

| Prueba | Qué comprueba |
|---|---|
| `test_el_refresh_de_otro_dispositivo_deja_de_renovar` | Con sesión en los dispositivos A y B, logout-todo desde A hace que el refresh de B ya no renueve: 401 `token_invalido`, sin tokens |
| `test_el_refresh_del_propio_dispositivo_tampoco_renueva` | El refresh del dispositivo A, desde el que se cerró la sesión, tampoco renueva |
| `test_logout_todo_incrementa_token_version_en_uno` | `token_version` del usuario sube exactamente en 1 |
| `test_logout_todo_se_registra_en_la_bitacora` | Queda un evento `logout_todo` en `EventoAuditoria` con el usuario y resultado `ok` |
| `test_sin_autenticacion_responde_401_y_no_cambia_token_version` | Sin token responde 401 `no_autenticado` (formato de `comun/errores.py`), no cambia `token_version` y no registra el evento |
| `test_un_login_nuevo_despues_de_logout_todo_si_renueva` | Un login nuevo después de logout-todo funciona y su refresh sí renueva |
| `test_logout_todo_dos_veces_no_falla_y_sube_token_version_en_dos` | Llamar logout-todo dos veces seguidas con el mismo access responde 200 las dos veces y `token_version` sube en 2 |

**Detalles:**

- Cada dispositivo es un `APIClient` distinto que hace `POST /api/v1/auth/login/` y se autentica con su access (`Authorization: Bearer ...`), igual que un cliente real.
- La renovación se prueba con `POST /api/v1/auth/token/renovar/` (ST-90), que rechaza un refresh cuyo `token_version` no coincide con el del usuario.
- La vista incrementa `token_version` con `update(token_version=F("token_version") + 1)` directo en la base, así que las pruebas usan `refresh_from_db()` antes de leerlo.
- La bitácora se verifica con `EventoAuditoria`, igual que `comun/tests/test_bitacora_flujos.py`.
- Usan los fixtures de `conftest.py`: `api_client`, `usuario` y `llaves` (par RS256 temporal).

### 4. Criterios de aceptación de HU-09 que validan

| Criterio | Pruebas |
|---|---|
| `POST /api/v1/auth/logout-todo/` incrementa `token_version` | `test_logout_todo_incrementa_token_version_en_uno`, `test_logout_todo_dos_veces_no_falla_y_sube_token_version_en_dos` |
| Ningún dispositivo puede renovar después | `test_el_refresh_de_otro_dispositivo_deja_de_renovar`, `test_el_refresh_del_propio_dispositivo_tampoco_renueva` |
| Se registra en la bitácora | `test_logout_todo_se_registra_en_la_bitacora` |

Además protegen que el endpoint exige autenticación y que una sesión nueva, iniciada después, no queda afectada.

### 5. Nota: el access ya emitido sigue sirviendo hasta 15 minutos

logout-todo invalida los **refresh**, no los **access** ya emitidos. `JWTAuthentication`, la autenticación del proyecto, no revisa `token_version`, así que un access emitido antes de logout-todo sigue siendo válido hasta que vence (15 minutos). Por eso la segunda llamada de `test_logout_todo_dos_veces_no_falla_y_sube_token_version_en_dos` responde 200.

El backlog no pide invalidar el access al momento, y ninguna prueba lo exige. Si en el futuro se requiere, habría que agregar una autenticación propia que compare el claim `token_version` del access con el del usuario.

### 6. Cómo correrlas

```bash
docker compose run --rm api pytest usuarios/tests/test_logout_todo.py -v   # solo estas pruebas
docker compose run --rm api pytest                                         # todo el proyecto
```

### 7. Resultado

Los criterios de aceptación de HU-09 quedan cubiertos por pruebas automáticas: logout-todo incrementa `token_version`, ningún dispositivo puede renovar después, el evento queda en la bitácora y una sesión nueva funciona con normalidad.

**ST-99 finalizada.**

**Responsable de la actividad:** Bryan Gael Esquivel Pérez (l22420415).
