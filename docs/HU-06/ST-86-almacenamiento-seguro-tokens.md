# HU-06 — Mantener la sesión iniciada ("recordarme")

## ST-86. Documentar el almacenamiento seguro de tokens para el frontend

**Estado:** Completada  
**Responsable:** Bryan Gael Esquivel Pérez (l22420415)

### 1. Descripción

Guía para el equipo de frontend sobre **dónde y cómo guardar los tokens** que entrega el microservicio de usuarios: cookie HttpOnly o sesión del gateway en web, almacenamiento seguro del sistema en móvil, y nunca `localStorage`.

Cubre el criterio de aceptación de HU-06: *"La API documenta que el cliente no debe guardar tokens en localStorage"*.

### 2. Qué tokens entrega la API

La API usa JWT de SimpleJWT firmados con **RS256** (`SIMPLE_JWT` en `config/settings.py`, emisor `svc-usuarios`).

| Token | Para qué sirve | Duración | Cómo se envía |
|---|---|---|---|
| **access** | Autoriza cada petición a la API | **15 minutos** (`ACCESS_TOKEN_LIFETIME`) | Encabezado `Authorization: Bearer <access>` |
| **refresh** | Pide un access nuevo cuando vence el anterior | **7 días** hoy (`REFRESH_TOKEN_LIFETIME`). Con ST-85: **7 días con "recordarme"** y **1 día sin él** | Solo al endpoint de renovación |

El refresh es el más delicado: quien lo tenga puede seguir obteniendo access nuevos durante días.

### 3. Regla principal: nunca `localStorage` ni `sessionStorage`

**No guardes el access ni el refresh en `localStorage` ni en `sessionStorage`.** Cualquier JavaScript que corra en la página puede leerlos. Si la aplicación sufre un XSS (un script inyectado por un comentario, una librería comprometida o una extensión), ese script roba los tokens y los usa desde otra máquina. Ningún ajuste de la API lo puede impedir después.

### 4. Dónde guardarlos

#### Web (recomendado)

| Token | Dónde | Por qué |
|---|---|---|
| access | **Solo en memoria**: una variable del estado de la app (store, contexto), nunca persistida | Dura 15 minutos; si se recarga la página se pide otro con el refresh |
| refresh | **Cookie `HttpOnly` + `Secure` + `SameSite=Strict`** (o `Lax` si hace falta navegación entre sitios), con un `Path` que cubra las rutas de autenticación del gateway/BFF que usan el refresh (renovar y cerrar sesión) | JavaScript no puede leerla; el navegador la envía solo por HTTPS, solo al mismo sitio y solo a esas rutas |

- La cookie la pone el **gateway o un backend-for-frontend (BFF)**, no el código del navegador. JavaScript nunca debe tener el refresh en sus manos.
- La cookie vive **entre el navegador y el gateway/BFF**. La API de ms-usuarios **nunca recibe el refresh como cookie**: el gateway/BFF lo lee de la cookie y lo manda a la API en el **cuerpo** de la petición.
- **`Path` de la cookie:** debe cubrir las rutas del gateway/BFF que necesitan el refresh, **renovar y cerrar sesión**, por ejemplo con un prefijo común como `/auth/`, y no todo el sitio (`/`). Si se limita solo a renovar, el logout no recibe la cookie y no puede invalidar el refresh.
- **Protección CSRF:** como el navegador envía la cookie automáticamente, el endpoint que la usa debe protegerse contra CSRF: `SameSite=Strict`/`Lax` más un token CSRF (patrón *double submit* o encabezado propio como `X-CSRF-Token`) y validación de `Origin`.

#### Alternativa: sesión del gateway

El navegador solo tiene una **cookie de sesión** (`HttpOnly`, `Secure`, `SameSite`). El gateway guarda el access y el refresh del lado del servidor, agrega el encabezado `Authorization` en cada petición a la API y renueva los tokens por su cuenta. El frontend nunca ve un JWT. Aplica la misma protección CSRF.

#### Móvil

| Plataforma | Dónde |
|---|---|
| iOS | **Keychain** |
| Android | **Keystore** o **EncryptedSharedPreferences** |

Nunca en `UserDefaults`, `SharedPreferences` sin cifrar, archivos ni bases locales en texto plano. El access puede vivir solo en memoria igual que en web.

### 5. Flujo recomendado

| Momento | Petición | Estado |
|---|---|---|
| Iniciar sesión | `POST /api/v1/auth/login/` → `{access, refresh}` | En desarrollo (HU-05) |
| Vence el access (401 `token_invalido`) | `POST /api/v1/auth/token/renovar/` con el refresh en el cuerpo → `{access, refresh}` | Endpoint en desarrollo (ST-90); la rotación y la lista negra ya están activas (ST-89) |
| Cerrar sesión | `POST /api/v1/auth/logout/` con el refresh en el cuerpo | Pendiente (HU-08) |

> Las rutas vienen del backlog; **login y renovar todavía están en desarrollo**, así que pueden ajustarse al implementarse. Hoy en `/api/v1/auth/` solo existe `registro/`.

1. Al iniciar sesión, guardar el access en memoria y el refresh en el lugar seguro (cookie del gateway/BFF o almacenamiento seguro del móvil).
2. Mandar el access en `Authorization: Bearer <access>`.
3. Si la API responde 401, renovar **una sola vez** y repetir la petición. Si varias peticiones fallan al mismo tiempo, hacer una sola renovación y que las demás esperen su resultado.
4. Al cerrar sesión, llamar a logout y borrar el access de memoria y el refresh del almacenamiento.

**Con el refresh en cookie (gateway/BFF):**

- **Renovar:** el BFF lee el refresh de la cookie, llama a `POST /api/v1/auth/token/renovar/` con el refresh en el cuerpo y **reemplaza la cookie** con el refresh nuevo que devuelve la API (por la rotación). Al frontend solo le entrega el access nuevo.
- **Cerrar sesión:** el BFF lee el refresh de la cookie, llama a `POST /api/v1/auth/logout/` con el refresh en el cuerpo para ponerlo en lista negra y **borra la cookie** con `Set-Cookie` usando `Max-Age=0` y el **mismo `Path`**. El frontend borra el access de memoria.

### 6. Rotación y lista negra (ST-89)

La rotación y la lista negra **ya están activas** en `development` (ST-89, PR #39): `config/settings.py` tiene `ROTATE_REFRESH_TOKENS` y `BLACKLIST_AFTER_ROTATION` en `True` y la app `token_blacklist` instalada. Lo que **todavía no existe** es el endpoint propio `POST /api/v1/auth/token/renovar/` y su serializer, que conservará la duración de "recordarme"; eso corresponde a **ST-90**.

Con esa configuración, toda renovación **rota** el refresh:

- Cada renovación entrega un **refresh nuevo** y el anterior queda en **lista negra**: deja de servir.
- El cliente debe **reemplazar siempre** el refresh guardado por el nuevo y **nunca reutilizar** el anterior. Usarlo otra vez responde error.
- Si una renovación responde error (refresh vencido, en lista negra o cuenta desactivada), **no reintentar**: borrar los tokens y mandar al usuario a iniciar sesión.

### 7. "Recordarme" (ST-85)

- Para el cliente **solo cambia la duración del refresh**: 7 días con "recordarme" y 1 día sin él. El access sigue durando 15 minutos.
- **No cambia dónde se guarda**: con o sin "recordarme", el refresh va en cookie HttpOnly, sesión del gateway o almacenamiento seguro del móvil. "Recordarme" nunca es motivo para usar `localStorage`.
- La rotación ya está activa (ST-89), así que el refresh renovado debe conservar la duración elegida en el login. Eso lo resolverá el serializer propio de renovación de ST-90, que todavía no existe.

### 8. Sí / No

| Sí | No |
|---|---|
| Access solo en memoria | Access o refresh en `localStorage` o `sessionStorage` |
| Refresh en cookie `HttpOnly` + `Secure` + `SameSite`, puesta por el gateway o BFF | Refresh en una cookie que JavaScript pueda leer, o puesta desde el navegador |
| Path de la cookie que cubra renovar y logout | Path limitado solo a renovar (el logout no recibiría la cookie) |
| Keychain / Keystore / EncryptedSharedPreferences en móvil | `UserDefaults`, `SharedPreferences` sin cifrar o archivos en texto plano |
| Reemplazar el refresh después de cada renovación | Reutilizar un refresh ya usado |
| Ante error al renovar, mandar a iniciar sesión | Reintentar la renovación en bucle |
| Protección CSRF si el refresh va en cookie | Confiar solo en la cookie sin CSRF |
| Enviar el access en `Authorization: Bearer` | Poner tokens en la URL, logs o mensajes de error |

### 9. Resultado

El equipo de frontend tiene documentado qué tokens entrega la API, por qué nunca deben ir en `localStorage`, dónde guardarlos en web y móvil, el flujo de login, renovación y cierre de sesión, y cómo afectan la rotación y "recordarme".

**ST-86 finalizada.**

**Responsable de la actividad:** Bryan Gael Esquivel Pérez (l22420415).
