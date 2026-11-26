# HU-33 / ST-219 · Verificar el ID token y crear o vincular la cuenta

**Subtarea:** ID 219 · [Backend] Verificar el ID token y crear o vincular la cuenta
**Historia padre:** HU-33 · Iniciar sesión con mi cuenta de Google
**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)
**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-220
**Estado:** En revisión
**Depende de:** ST-218 (`GOOGLE_CLIENT_ID`)

## Endpoint

`POST /api/v1/auth/google/` · público (`AllowAny`) · mismo límite de intentos que el login (`throttle_scope = "login"`).

```json
{ "id_token": "<ID token que el frontend recibió de Google>", "recordarme": false, "acepto_privacidad": false }
```

| Campo | Obligatorio | Para qué |
| --- | --- | --- |
| `id_token` | Sí | El token que entrega el botón de Google al frontend |
| `recordarme` | No | Igual que el login: refresh de 7 días en vez de 1 (HU-06) |
| `acepto_privacidad` | No | Solo cuenta si **se crea** la cuenta: guarda fecha y versión del aviso (HU-02) |

**Respuesta 200:** lo mismo que `POST /api/v1/auth/login/` (`access`, `refresh`, `usuario`), o `requiere_2fa` + `token_temporal` si la cuenta tiene 2FA, más:

```json
{ "cuenta_nueva": true }
```

## Cómo funciona

1. **Verificar** (`usuarios/login_google.py` → `verificar_id_token()`), con
   `google.oauth2.id_token.verify_oauth2_token(token, Request(), settings.GOOGLE_CLIENT_ID)`:
   - firma de Google, emisor (`iss`), vencimiento (`exp`) y **audiencia (`aud`) = nuestro `GOOGLE_CLIENT_ID`**;
   - además, el correo debe venir con `email_verified = true`.
   - Si `GOOGLE_CLIENT_ID` está vacío **no se verifica nada** y responde 503. Con la audiencia vacía, google-auth aceptaría tokens de cualquier otra app.
2. **Crear o vincular** (`obtener_o_crear_usuario()`), buscando por correo sin importar mayúsculas:

   | Situación | Qué pasa |
   | --- | --- |
   | Correo nuevo | Se crea un **Cliente activo**, con `email_verificado=True` y **sin contraseña usable** (`set_password(None)`). Nombre y apellidos de Google. |
   | Cuenta activa | Se **vincula**: entra con esa cuenta. No se toca su contraseña ni su rol. |
   | Cuenta pendiente | Google ya verificó el correo → se activa y entra. |
   | Cuenta inactiva | 403 `cuenta_inactiva`, igual que con contraseña. |
3. **Terminar el login** con `completar_login()` (`usuarios/tokens.py`), **la misma función que usa el login con contraseña**:
   aviso de dispositivo nuevo (HU-28), 2FA si está activo (HU-31), registro del acceso (HU-22), JWT con los mismos claims y "recordarme" (HU-06).

> `completar_login()` es el final del `validate()` de `CustomTokenObtainPairSerializer` movido a una función, sin cambiar su lógica. Así el login con contraseña y el de Google no se separan con el tiempo.

## Errores

| Código | HTTP | Cuándo |
| --- | --- | --- |
| `datos_invalidos` | 400 | Falta `id_token` |
| `token_google_invalido` | 401 | Firma, audiencia, emisor o vencimiento incorrectos, o correo no verificado |
| `cuenta_inactiva` | 403 | La cuenta existe pero está desactivada |
| `google_no_configurado` | 503 | Falta `GOOGLE_CLIENT_ID` o no se pudo consultar a Google |

Ambos códigos nuevos están en `docs/catalogo-errores.md` y en `comun/errores.py`.

## Dependencias nuevas

`google-auth==2.63.1` y `requests==2.34.2` (transporte HTTP que usa google-auth para descargar las llaves públicas de Google). Después de hacer pull: `docker compose up -d --build`.

## Decisiones

- **No se guarda el `sub` de Google.** "Vincular" es iniciar sesión con la cuenta del mismo correo verificado; no hace falta un campo nuevo ni migración. Si más adelante se quiere permitir cambiar el correo sin perder el vínculo con Google, se agrega `google_sub` a `Usuario` (lo fusiona el profesor).
- **Aviso de privacidad:** si la cuenta se crea sin `acepto_privacidad`, queda sin fecha de aceptación, y el frontend puede pedirla después con `POST /api/v1/auth/privacidad/aceptar/` (HU-29). `cuenta_nueva: true` le avisa que acaba de crearse.
- **Teléfono:** Google no lo da; la cuenta nueva queda sin teléfono, con canal `correo`.

## Cómo probarlo

```bash
docker compose up -d --build
docker compose exec api pytest usuarios/tests/test_login_google.py -v   # 27 passed
docker compose exec api pytest
```

Las pruebas no salen a internet:
- la mayoría simulan `verify_oauth2_token`;
- 5 **firman un ID token de verdad** con una llave propia y hacen pasar su certificado por el de Google, para comprobar que google-auth rechaza audiencia de otra app, emisor falso, token vencido y firma alterada.

**Con Google real:** con `GOOGLE_CLIENT_ID` en el `.env` y tu Gmail como usuario de prueba (ST-218), obtén un ID token desde el frontend (o con [Google OAuth Playground](https://developers.google.com/oauthplayground) usando tu propio client ID) y envíalo en Swagger a `POST /api/v1/auth/google/`.