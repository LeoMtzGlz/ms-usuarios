# HU-06 — Mantener la sesión iniciada ("recordarme")

## ST-87. Pruebas de la expiración del refresh con y sin "recordarme"

**Estado:** Completada  
**Responsable:** Bryan Gael Esquivel Pérez (l22420415)

### 1. Descripción

Se agregaron las pruebas automáticas de "recordarme" en el login (ST-85). Hacen peticiones reales a `POST /api/v1/auth/login/` y revisan los tokens que entrega la API: cuánto dura el refresh con y sin "recordarme", que el access siga en 15 minutos, que el registro de la lista negra venza igual que el token y que los errores sigan saliendo con el formato del equipo.

No se modificó código de la aplicación: solo se agregan pruebas.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_recordarme.py` | Pruebas de la duración del refresh según "recordarme" |

### 3. Qué cubre cada prueba

| Prueba | Qué comprueba |
|---|---|
| `test_sin_recordarme_el_refresh_dura_un_dia` | Sin mandar `recordarme`, el refresh dura 1 día y su claim `recordarme` es `False` |
| `test_recordarme_false_explicito_dura_un_dia` | Con `"recordarme": false`, el refresh dura 1 día |
| `test_con_recordarme_el_refresh_dura_siete_dias` | Con `"recordarme": true`, el refresh dura 7 días y su claim `recordarme` es `True` |
| `test_el_access_dura_quince_minutos_en_todos_los_casos` | En los tres casos anteriores el access dura 15 minutos (prueba parametrizada) |
| `test_outstanding_token_vence_igual_que_el_refresh` | `OutstandingToken.expires_at`, buscado por el `jti`, coincide con el `exp` del refresh entregado, con y sin "recordarme" (parametrizada) |
| `test_recordarme_no_booleano_responde_400_sin_tokens` | `"recordarme": "quizas"` responde 400 con `codigo: datos_invalidos` y el campo `recordarme` en `campos` (formato de `comun/errores.py`), sin access ni refresh |
| `test_credenciales_invalidas_con_recordarme_siguen_fallando` | Con contraseña incorrecta y `"recordarme": true` sigue respondiendo 401 `credenciales_invalidas`: "recordarme" no cambia la validación |

**Detalles:**

- Usan los fixtures de `conftest.py`: `api_client`, `usuario` (activo, contraseña `PASSWORD_PRUEBA`) y `llaves` (par RS256 temporal; no necesitan `llaves/privada.pem`).
- Los tokens se leen con `RefreshToken` y `AccessToken` de SimpleJWT, que además verifican la firma.
- Las duraciones se comparan con **±1 segundo** de tolerancia, igual que `test_jwt_rs256.py`, para que no fallen cuando `iat` y `exp` caen en segundos distintos.
- django-axes no interfiere: guarda los intentos en la base y cada prueba corre en su propia transacción, así que el único intento fallido no bloquea a nadie. No se desactivó nada.

### 4. Cómo correrlas

```bash
docker compose run --rm api pytest usuarios/tests/test_recordarme.py -v   # solo estas pruebas
docker compose run --rm api pytest                                        # todo el proyecto
```

### 5. Criterios de aceptación de HU-06 que validan

| Criterio | Pruebas |
|---|---|
| El login acepta `recordarme`, falso por defecto | `test_sin_recordarme_el_refresh_dura_un_dia`, `test_recordarme_false_explicito_dura_un_dia`, `test_recordarme_no_booleano_responde_400_sin_tokens` |
| Con "recordarme" la renovación dura 7 días | `test_con_recordarme_el_refresh_dura_siete_dias` |
| Sin "recordarme" la renovación dura 1 día | `test_sin_recordarme_el_refresh_dura_un_dia`, `test_recordarme_false_explicito_dura_un_dia` |

Además protegen lo que ST-85 no debe cambiar: el access de 15 minutos, la validación de credenciales y el formato de errores. También comprueban el registro en `OutstandingToken`, que necesita la limpieza de tokens vencidos (ST-91).

### 6. Resultado

Los criterios de aceptación de HU-06 sobre "recordarme" quedan cubiertos por pruebas automáticas que corren en el CI contra PostgreSQL 16.

**ST-87 finalizada.**

**Responsable de la actividad:** Bryan Gael Esquivel Pérez (l22420415).
