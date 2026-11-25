# HU-31 — Iniciar sesión con el segundo factor

## ST-210. Devolver el token temporal en el login

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Cuando el usuario tiene el 2FA confirmado, `POST /api/v1/auth/login/` ya no entrega los JWT. Entrega un token temporal de 5 minutos, firmado con `TimestampSigner` y un salt propio, que solo sirve para completar el inicio de sesión con el código de la app en `POST /api/v1/auth/2fa/verificar/` (st-211). Cubre el criterio 1 de HU-31.

Depende de st-82 (login), st-85 (recordarme), st-205 (`Dispositivo2FA`) y st-208, ya integradas en `development`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/login_2fa.py` | Nuevo: `tiene_2fa_activo()`, `emitir_token_temporal()` y `leer_token_temporal()` |
| `usuarios/tokens.py` | 2 importaciones y un bloque de 8 líneas en `validate()`, marcados con `# t-31/st-210` |
| `usuarios/tests/test_token_temporal_2fa.py` | Nuevo: 14 pruebas |

No se modificó ningún modelo ni se creó ninguna migración.

### 3. Respuesta del login

Sin 2FA, o con el 2FA iniciado pero sin confirmar, la respuesta no cambia (`access`, `refresh` y `usuario`). Con el 2FA confirmado:

```json
{
  "requiere_2fa": true,
  "token_temporal": "eyJ1aWQiOi...:1t5x...:abc...",
  "expira_en": 300
}
```

### 4. Cómo funciona

- El token lleva el id del usuario, su `token_version` y la opción `recordarme` del login (st-85). Se firma con `TimestampSigner(salt="ms-usuarios.login-2fa")`, así que no sirve como JWT ni con ninguna otra firma del proyecto.
- `leer_token_temporal(token)` devuelve `(usuario, recordarme)` o lanza `TokenInvalido` (401, `token_invalido`) si el token:
  - está alterado o se firmó con otro salt;
  - tiene más de 5 minutos;
  - es de una cuenta que ya no está activa;
  - tiene un `token_version` distinto, por ejemplo porque el usuario cerró todas sus sesiones o cambió su contraseña.
- La función `leer_token_temporal()` la usará la st-211 para validar el token antes de revisar el código, y `recordarme` para emitir el refresh con la duración que el usuario eligió (7 días o 1).
- El bloque se ejecuta después de validar la contraseña y el estado de la cuenta, así que una contraseña incorrecta sigue respondiendo `credenciales_invalidas` y no entrega ningún token.

### 5. Decisiones

- Con 2FA **no** se actualiza `last_login` ni se registra un acceso exitoso en `RegistroAcceso`: el inicio de sesión todavía no termina. Eso lo hará la st-211 cuando el código sea correcto.
- Se registra el evento `login_requiere_2fa` en la bitácora, sin el token.
- Se reutiliza el error `TokenInvalido` del catálogo; no se agregaron códigos nuevos a `comun/errores.py`.

### 6. Pruebas

```bash
docker compose run --rm api pytest usuarios/tests/test_token_temporal_2fa.py -v
```

| Prueba | Qué verifica |
|---|---|
| `test_sin_2fa_el_login_entrega_los_jwt` | Sin 2FA el login no cambia |
| `test_con_2fa_el_login_entrega_token_temporal_y_no_los_jwt` | Con 2FA confirmado: `requiere_2fa`, `token_temporal` y `expira_en` = 300, sin `access` ni `refresh` |
| `test_2fa_sin_confirmar_no_cambia_el_login` | Un 2FA iniciado pero sin confirmar no cuenta |
| `test_con_2fa_y_contrasena_incorrecta_no_hay_token_temporal` | Contraseña incorrecta: 401 `credenciales_invalidas` |
| `test_con_2fa_no_se_actualiza_last_login` | El primer paso no cuenta como inicio de sesión |
| `test_registra_el_evento_sin_el_token` | Evento `login_requiere_2fa`, sin el token en la bitácora |
| `test_el_token_identifica_al_usuario` | El token devuelve al usuario correcto |
| `test_el_token_conserva_la_opcion_recordarme_del_login` (2 casos) | Guarda `recordarme` = true o false tal como llegó al login |
| `test_el_token_vence_a_los_5_minutos` | Después de 300 s responde `TokenInvalido` |
| `test_el_token_alterado_se_rechaza` | Una firma modificada no sirve |
| `test_un_token_firmado_con_otro_salt_se_rechaza` | Una firma de otro salt no sirve |
| `test_el_token_deja_de_servir_si_cambia_token_version` | Cerrar todas las sesiones invalida el token |
| `test_el_token_no_sirve_si_la_cuenta_ya_no_esta_activa` | Una cuenta desactivada no puede continuar |

### 7. Resultado

El login entrega el token temporal cuando el usuario tiene 2FA, con 14 pruebas en verde. Continúa con la st-211 (endpoint de verificación) y la st-212 (pruebas de HU-31).

**ST-210 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).
