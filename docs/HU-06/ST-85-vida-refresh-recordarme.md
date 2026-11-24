# HU-06 — Mantener la sesión iniciada ("recordarme")

## ST-85. Ajustar la vida del refresh según "recordarme"

**Estado:** Completada  
**Responsable:** Bryan Gael Esquivel Pérez (l22420415)

### 1. Descripción

El login (`POST /api/v1/auth/login/`, ST-82) ahora acepta el campo opcional `recordarme`. Según su valor, el token de renovación (*refresh*) dura **7 días** o **1 día**, como pide HU-06. Se implementa en `CustomTokenObtainPairSerializer` (`usuarios/tokens.py`) con `RefreshToken.set_exp(lifetime=...)` al emitir el token, como indica el backlog.

No cambian la vista ni la ruta del login, ni la lógica de claims, errores y registro de accesos (t-22/st-167).

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tokens.py` | Campo `recordarme` (falso por defecto), constantes de duración, `set_exp(lifetime=...)`, claim `recordarme` y ajuste de `OutstandingToken.expires_at` |

### 3. Cómo se manda "recordarme"

```http
POST /api/v1/auth/login/
Content-Type: application/json

{"email": "ana@ejemplo.com", "password": "Secreta123", "recordarme": true}
```

- `recordarme` es **opcional** y **falso por defecto**: si no se manda, el refresh dura 1 día.
- Acepta los valores booleanos de DRF (`true`/`false`, `1`/`0`, `"true"`/`"false"`).
- La respuesta tiene la misma forma que antes: `{access, refresh, usuario}`.

### 4. Duraciones

| Token | Sin `recordarme` | Con `recordarme` |
|---|---|---|
| refresh | **1 día** (`DURACION_REFRESH_SIN_RECORDARME`) | **7 días** (`DURACION_REFRESH_CON_RECORDARME`) |
| access | 15 minutos | 15 minutos |

Las constantes viven en `usuarios/tokens.py`. `REFRESH_TOKEN_LIFETIME` de `config/settings.py` (7 días) no se modificó: sigue siendo la duración por defecto de SimpleJWT para cualquier refresh que no pase por el login.

### 5. Claim `recordarme`

El refresh lleva el claim `"recordarme": true | false`.

**Por qué existe:** con la rotación activa (ST-89), al renovar SimpleJWT emite un refresh nuevo con `REFRESH_TOKEN_LIFETIME` global (7 días). Sin este claim, un refresh de 1 día se convertiría en uno de 7 días en la primera renovación. El serializer propio de renovación (**ST-90**) debe leer el claim y aplicar la misma duración al refresh rotado.

El access también hereda el claim, porque SimpleJWT copia al access los claims del refresh (salvo `token_type`, `exp`, `iat` y `jti`). No afecta a nada: el access sigue durando 15 minutos.

### 6. Registro en `OutstandingToken`

Con `token_blacklist` activo (ST-89), `RefreshToken.for_user()` registra cada refresh en `OutstandingToken` con `expires_at` calculado con la duración por defecto (7 días), **antes** de que el login ajuste la duración. Por eso, después de `set_exp()`, el login actualiza ese registro (buscándolo por su `jti`) para que `expires_at` coincida con el `exp` real del token.

Así, la limpieza de tokens vencidos (**ST-91**, `flushexpiredtokens`) borra los refresh de 1 día cuando de verdad vencen y no 6 días después.

### 7. Pruebas

Las pruebas formales de "recordarme" corresponden a **ST-87**: duración de 1 y 7 días, valor por defecto, claim `recordarme`, access de 15 minutos y `OutstandingToken.expires_at`. En esta subtarea se verificó que las pruebas existentes siguen pasando y se comprobó el comportamiento a mano.

### 8. Resultado

El login acepta `recordarme` (falso por defecto): el refresh dura 7 días con él y 1 día sin él, lleva el claim `recordarme` para que la renovación de ST-90 conserve la duración, y su registro en `OutstandingToken` vence cuando vence el token.

**ST-85 finalizada.**

**Responsable de la actividad:** Bryan Gael Esquivel Pérez (l22420415).
