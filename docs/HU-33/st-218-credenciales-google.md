# HU-33 / ST-218 · Credenciales OAuth de Google

**Subtarea:** ID 218 · [Configuración] Crear las credenciales OAuth en Google Cloud Console
**Historia padre:** HU-33 · Iniciar sesión con mi cuenta de Google
**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)
**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-220
**Estado:** En revisión

## Descripción

Para HU-33, el **frontend** muestra el botón "Iniciar sesión con Google", Google le entrega un **ID token**, y el frontend lo manda a `POST /api/v1/auth/google/`. El backend verifica ese token con `google-auth` (ST-219).

Para eso hace falta un **ID de cliente OAuth** de Google:
- el frontend lo usa para mostrar el botón;
- el backend lo usa para comprobar que el token se emitió **para nuestra app** (campo `aud`).

Esta subtarea crea ese cliente en Google Cloud Console y deja su valor en `GOOGLE_CLIENT_ID`.

```text
Frontend ──(botón de Google con GOOGLE_CLIENT_ID)──▶ Google ──ID token──▶ Frontend
Frontend ──POST /api/v1/auth/google/ {id_token}──▶ svc-usuarios
svc-usuarios: verify_oauth2_token(id_token, ..., GOOGLE_CLIENT_ID)  ← ST-219
```

## Qué cambia en el repositorio

| Archivo | Cambio |
| --- | --- |
| `config/settings.py` | `GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")` ⚠️ Toca `config/`: lo fusiona el profesor (regla 7) |
| `.env.example` | Variable `GOOGLE_CLIENT_ID=` vacía, con comentario |
| `usuarios/tests/test_google_config.py` | Comprueba que la variable se lee del entorno y que por defecto está vacía |

No agrega dependencias: `google-auth` se instala en la ST-219, que es la que lo usa.

---

## Pasos en Google Cloud Console

Hazlo con la cuenta de Google **del proyecto o del equipo**, no con una personal que luego se pierda, y comparte el acceso al proyecto con quien lo vaya a mantener.

### 1. Crear o elegir el proyecto
1. Entra a <https://console.cloud.google.com/> e inicia sesión.
2. Arriba, en el selector de proyectos → **Proyecto nuevo**. Nombre sugerido: `svc-usuarios`.

### 2. Registrar la app en Google Auth Platform (Branding y Audience)
Google pide registrar la app **antes** de poder crear el cliente.

1. Menú → **APIs y servicios → Pantalla de consentimiento de OAuth** (en la consola nueva aparece como **Google Auth Platform**). Haz clic en **Comenzar**.
2. **Información de la app** (Branding):
   - Nombre de la app: el del sistema (lo verá la persona en la ventana de Google).
   - Correo de asistencia al usuario: el correo del equipo.
3. **Público** (Audience): **Externo**. Así puede entrar cualquier cuenta de Google, no solo las de una organización.
4. **Información de contacto**: el correo del equipo.
5. Acepta la política de datos del usuario y haz clic en **Crear**.
6. En **Público**, mientras la app esté en estado **Prueba** (Testing), solo pueden iniciar sesión los **usuarios de prueba**. Agrega ahí los correos de Gmail del equipo.

> Solo pedimos los permisos básicos (`openid`, `email`, `profile`), así que no hace falta verificar la app con Google para desarrollo.

### 3. Crear el cliente OAuth
1. **Google Auth Platform → Clientes** → **Crear cliente**.
2. **Tipo de aplicación:** **Aplicación web**.
3. **Nombre:** `svc-usuarios web (desarrollo)`.
4. **Orígenes autorizados de JavaScript:** las direcciones desde donde el **frontend** muestra el botón. Para pruebas, Google pide agregar tanto `http://localhost` como `http://localhost:<puerto>`.

   | Origen | Para qué |
   | --- | --- |
   | `http://localhost` | Pruebas locales |
   | `http://localhost:<puerto del frontend>` | El puerto real del frontend (por ejemplo `5173` con Vite o `3000` con React). **Confírmalo con el equipo de frontend.** |
   | `https://<dominio del sistema>` | Cuando haya un servidor público |

   Reglas de Google para los orígenes:
   - HTTPS obligatorio, salvo `localhost`.
   - Sin rutas, `?parámetros` ni `#fragmentos`.
   - Sin comodines (`*`).
   - Sin IPs, salvo las de localhost.

5. **URIs de redireccionamiento autorizados:** **déjalo vacío**. El botón de Google devuelve el token por JavaScript; no redirige al backend.
6. Haz clic en **Crear**.

### 4. Copiar el ID de cliente
Aparece una ventana con:
- **ID de cliente:** termina en `.apps.googleusercontent.com` → **este es el que usamos**.
- **Secreto del cliente:** **no lo usamos**. Verificar un ID token solo necesita el ID de cliente. No lo copies a ningún archivo del repositorio, chat ni documento.

> Si cambias los orígenes después, pueden tardar de 5 minutos a unas horas en aplicarse. Si sale el error `origin_mismatch`, revisa que el origen coincida exactamente, incluido el puerto.

### 5. Ponerlo en el `.env`
En tu `.env` (no en `.env.example`):

```text
GOOGLE_CLIENT_ID=123456789012-abc123def456.apps.googleusercontent.com
```

Reinicia la API para que lo lea:

```bash
docker compose restart api
docker compose exec api python manage.py shell -c "from django.conf import settings; print(settings.GOOGLE_CLIENT_ID)"
```

### 6. Compartirlo con el equipo
- El **ID de cliente** no es secreto: el frontend lo pone en su código y cualquiera puede verlo en el navegador. Se comparte con el equipo de **frontend** y con quien lo necesite en su `.env`.
- Aun así, `.env.example` lo deja vacío para que cada entorno (desarrollo, servidor) use el suyo.
- El **secreto del cliente** nunca se comparte ni se sube.

---

## Para la ST-219 (verificar el ID token)

```python
from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token

idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
```

- `verify_oauth2_token` comprueba la firma, que `aud` sea **nuestro** `GOOGLE_CLIENT_ID` y que no haya expirado.
- Si `GOOGLE_CLIENT_ID` está vacío, el endpoint debe responder un error claro (login con Google no configurado) en lugar de intentar verificar.
- Verificar necesita salir a internet para descargar las llaves públicas de Google; en las pruebas (ST-220) se simula.
- Agregar `google-auth` a `requirements.txt` con versión fija.

## Checklist de la subtarea
- [ ] Proyecto creado en Google Cloud Console con la cuenta del equipo
- [ ] App registrada: Externo, en modo Prueba, con los usuarios de prueba del equipo
- [ ] Cliente **Aplicación web** con los orígenes del frontend
- [ ] `GOOGLE_CLIENT_ID` en el `.env` local y compartido con el frontend
- [ ] El secreto del cliente **no** está en el repositorio