# HU-31 — Iniciar sesión con el segundo factor

## ST-211. Crear el endpoint de verificación

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se creó `POST /api/v1/auth/2fa/verificar/`, el segundo paso del login con 2FA. Recibe el token temporal que entrega el login (st-210) y un código:

- el de 6 dígitos de la app autenticadora, o
- uno de los códigos de respaldo (st-207), que se consume al usarlo.

Si el código es correcto, se completa el inicio de sesión: se registra el acceso, se actualiza `last_login` y se entregan los JWT, igual que en el login normal y con la duración de "recordarme" (st-85).

Depende de st-206 (`Dispositivo2FA.ultimo_intervalo`), st-207 (`usar_codigo_respaldo`), st-210 (token temporal), st-167 (historial de accesos) y st-85 (recordarme), ya integradas en `development`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/views_2fa_verificar.py` | Nuevo: `VerificarDosFactoresView`, su serializer y el de la respuesta para Swagger |
| `usuarios/urls.py` | Una importación y una ruta, marcadas con `# t-31/st-211` |
| `usuarios/tokens.py` | Al final, la función `emitir_jwt()`, marcada con `# t-31/st-211`; no se modificó nada del login |
| `usuarios/tests/test_autorizacion_endpoints.py` (st-129) | Dos líneas, marcadas con `# t-31/st-211`, para clasificar la ruta nueva como pública |
| `usuarios/tests/test_verificar_2fa.py` | Nuevo: 23 pruebas |

No se modificó ningún modelo ni se creó ninguna migración.

### 3. Uso

```http
POST /api/v1/auth/2fa/verificar/
Content-Type: application/json

{"token_temporal": "<token del login>", "codigo": "123456"}
```

El código también puede ser uno de respaldo, con o sin guion (`ABC-DEF`).

Respuesta `200`, la misma que el login:

```json
{
  "access": "...",
  "refresh": "...",
  "usuario": {"id": "6f1c…", "nombre": "Ana", "email": "ana@ejemplo.com", "rol": "cliente"}
}
```

| Caso | Respuesta |
|---|---|
| Faltan `token_temporal` o `codigo` | `400 datos_invalidos` |
| Código incorrecto, repetido o de respaldo ya usado | `400 codigo_invalido` |
| Token temporal alterado, vencido, ya usado, cuenta no activa o 2FA desactivado | `401 token_invalido` |
| Más de 5 códigos incorrectos | `429 demasiados_intentos` con `Retry-After` |

### 4. Cómo funciona

- **Es pública** (`AllowAny` y `authentication_classes = []`, como las demás rutas públicas): el usuario todavía no tiene JWT y un encabezado `Authorization` inválido se ignora. Se identifica con el token temporal, que `leer_token_temporal()` valida (firma, 5 minutos, cuenta activa y `token_version`). `get_authenticate_header()` devuelve `Bearer realm="api"` para que `token_invalido` siga respondiendo 401 y no 403, igual que la renovación de tokens.
- **El mismo código de la app no sirve dos veces** (HU-31, criterio 3): se acepta el intervalo actual o uno de al lado, como en st-206, pero solo si es posterior al guardado en `Dispositivo2FA.ultimo_intervalo`. Al aceptarlo se guarda ese intervalo. Así tampoco sirve el código con el que se confirmó el 2FA.
- **Códigos de respaldo:** se validan con `usar_codigo_respaldo()` (st-207), que los marca como usados. Como el alfabeto de respaldo incluye los números 2-9, un código puede ser solo de números (por ejemplo `234-567` escrito sin guion): si un código de 6 dígitos no es el de la app, se prueba como código de respaldo. Cuenta como un solo intento.
- **Máximo 5 intentos** (HU-31, criterio 3): los códigos incorrectos se cuentan por usuario durante 5 minutos en la caché del proyecto (`cache_table`, st-178). Después del quinto se responde `429` con `Retry-After` (como en HU-24) aunque el código sea correcto, y un login nuevo no reinicia la cuenta. Un código correcto la reinicia.
- **El token temporal es de un solo uso:** después de un inicio de sesión correcto se marca como usado en la caché.
- **Peticiones simultáneas:** se bloquea la fila de `Dispositivo2FA` (`select_for_update`), así que dos peticiones con el mismo código no pueden pasar las dos.
- **Historial y bitácora:** cada intento queda en el historial de accesos (st-167) como exitoso o fallido. Se registran los eventos `login_2fa_completado` y `login_2fa_fallido` con el método (`app` o `respaldo`), y `login_2fa_bloqueado` al pasar los 5 intentos, sin el código ni el token.
- **Tokens:** se emiten con `emitir_jwt()`, una función nueva al final de `tokens.py` que hace los mismos pasos que el login: los claims de `CustomTokenObtainPairSerializer.get_token()` y la duración del refresh según "recordarme". El login no se modificó; en otra subtarea su responsable puede hacer que `validate()` también la use.

### 5. Pruebas

```bash
docker compose run --rm api pytest usuarios/tests/test_verificar_2fa.py -v
```

Resultado: **23 passed**.

| Grupo | Pruebas |
|---|---|
| Código correcto | Código de la app, código de respaldo, código de respaldo solo de números, registro del acceso y `last_login`, "recordarme" (7 días o 1 día), mismos claims que el login |
| Incorrecto o repetido | Código incorrecto, el mismo código dos veces, el código usado al confirmar el 2FA, un código de respaldo dos veces |
| Máximo 5 intentos | El quinto todavía se evalúa; después de 5 se bloquea aunque el código sea correcto; un login nuevo no reinicia los intentos |
| Token temporal | De un solo uso, inválido, 2FA desactivado, faltan datos |
| Ruta pública | Un `Authorization: Bearer token-invalido` se ignora: llega a la validación (400) y deja verificar (200) |
| Swagger | Documenta las respuestas 200, 400, 401 y 429 |
| Bitácora | No guarda el código ni el token; registra el bloqueo |

Las pruebas de la HU completa (correcto, incorrecto, repetido y respaldo de un solo uso) son de la st-212.

### 6. Resultado

El login con 2FA queda completo: con el token temporal y un código correcto se entregan los JWT, el mismo código no se puede usar dos veces y hay un máximo de 5 intentos.

### 7. Notas

- En Swagger (`/api/docs/`) la ruta documenta la respuesta `200` (igual que el login) y los errores `400`, `401` y `429`.

- La tabla de la caché se crea con `python manage.py createcachetable`, que ya corre el `Dockerfile` (st-179). Las pruebas la crean solas.