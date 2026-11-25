# HU-32 / ST-215 · Crear el endpoint de desactivar 2FA para clientes

**Subtarea:** ID 215 · [Backend] Crear el endpoint de desactivar 2FA para clientes
**Historia:** HU-32 · Exigir 2FA a los administradores
**Responsable:** Isamar Chávez Díaz (chamar29) · **Revisa:** Isis Vázquez (isis0015)
**Rama:** `t-32/st-215`
**Estado:** En revisión

## Descripción

Un cliente u operativo puede desactivar su verificación en dos pasos. Para hacerlo pide **la
contraseña y un código de la app**, y al terminar **se avisa por correo**. Un **administrador
no puede desactivarla** (criterio de HU-32), como dice la matriz de la ST-127:
*"Desactivar 2FA · Cliente u operativo propietario; no administrador · HU-32 / ST-215"*.

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `usuarios/views_2fa_desactivar.py` | `Desactivar2FASerializer`, `intervalo_del_codigo()` y `Desactivar2FAView` (archivo nuevo, para no chocar con `views_2fa.py`) |
| `usuarios/urls.py` | Ruta `2fa/desactivar/` (líneas `# t-32/st-215`) |
| `comun/errores.py` | Errores `DosFactoresNoActivo` y `AdminRequiere2FA` (bloque `# t-32/st-215`) |
| `notificaciones/templates/notificaciones/2fa_desactivado.txt` | Texto del aviso por correo |
| `usuarios/tests/test_desactivar_2fa.py` | 20 pruebas |

No hay modelos nuevos ni migraciones.

## Endpoint

`POST /api/v1/auth/2fa/desactivar/` · requiere sesión (JWT)

```json
{ "password": "MiContraseña123", "codigo": "123456" }
```

### Respuestas

| Código | Cuándo | `codigo` del error |
| --- | --- | --- |
| 200 | Se desactivó | — `{"desactivado": true, "mensaje": "Verificación en dos pasos desactivada."}` |
| 400 | Contraseña incorrecta | `datos_invalidos`, con `campos.password` |
| 400 | Código incorrecto o ya usado | `codigo_invalido` |
| 400 | El código no tiene 6 dígitos o faltan datos | `datos_invalidos`, con `campos` |
| 400 | No tiene 2FA activo (o lo inició sin confirmar) | `dos_factores_no_activo` |
| 401 | Sin sesión | `no_autenticado` |
| 403 | Es administrador | `admin_requiere_2fa` |

## Cómo funciona

1. Si el usuario es **administrador**, responde 403 y no toca nada.
2. Revisa el formato (contraseña y código de 6 dígitos).
3. Verifica la **contraseña** con `check_password`.
4. Bloquea su `Dispositivo2FA` confirmado (`select_for_update`) y verifica el **código**:
   - acepta el código actual, el anterior o el siguiente (30 s cada uno), igual que `verificar()`;
   - un código **ya usado** (`intervalo <= ultimo_intervalo`) no sirve otra vez.
5. Si todo está bien, en una sola transacción: borra el `Dispositivo2FA` (secreto cifrado),
   borra los **códigos de respaldo** y **encola el aviso por correo** (`notificar`, plantilla
   `2fa_desactivado`, canal `correo`). El worker lo envía.
6. Registra en la bitácora `2fa_desactivado` (o `2fa_desactivacion_fallida` /
   `2fa_desactivacion_rechazada`). Nunca se registra la contraseña ni el código.

Después de desactivarlo, el usuario puede volver a activarlo con `POST /api/v1/auth/2fa/activar/`.

### Decisiones

- **Solo código de la app, no código de respaldo.** La subtarea pide "contraseña y código". Si el
  equipo decide aceptar también los de respaldo, se puede agregar con `usar_codigo_respaldo()`.
- **El aviso no lleva datos secretos:** solo nombre, fecha y asunto.
- **Archivo aparte** (`views_2fa_desactivar.py`) para no chocar con las ST-210/211 que editan `views_2fa.py`.

## Cómo probarlo

```powershell
$env:SECRET_KEY = "clave-de-prueba"
$env:DATABASE_URL = "sqlite:///prueba.db"
python -m pytest usuarios/tests/test_desactivar_2fa.py -v
Remove-Item prueba.db
```

En Swagger (`/api/docs/`): iniciar sesión, activar y confirmar el 2FA, y luego llamar a
`POST /api/v1/auth/2fa/desactivar/` con la contraseña y el código de la app.

## Pruebas (20)

| Prueba | Resultado |
| --- | --- |
| Cliente desactiva con contraseña y código → 200 y se borra el dispositivo | ✅ |
| Se borran los 10 códigos de respaldo | ✅ |
| Un operativo también puede | ✅ |
| Se encola el aviso por correo (canal `correo`, plantilla `2fa_desactivado`) | ✅ |
| El aviso se arma con la plantilla del worker y no lleva contraseña, código ni secreto | ✅ |
| Después se puede volver a activar | ✅ |
| La bitácora registra `2fa_desactivado` sin contraseña ni código | ✅ |
| Administrador → 403 `admin_requiere_2fa` y su 2FA sigue activo | ✅ |
| Sin sesión → 401 | ✅ |
| Contraseña incorrecta → 400 y nada cambia | ✅ |
| Código incorrecto → 400 y nada cambia | ✅ |
| Código ya usado → 400 y nada cambia | ✅ |
| Formato de código inválido (4 casos) → 400 | ✅ |
| Faltan datos → 400 con `password` y `codigo` | ✅ |
| Sin 2FA → 400 `dos_factores_no_activo` | ✅ |
| 2FA iniciado sin confirmar → 400 `dos_factores_no_activo` | ✅ |
| `intervalo_del_codigo` acepta el anterior y rechaza uno viejo | ✅ |

## Checklist

- [x] `python -m ruff check .` sin errores
- [x] `python manage.py makemigrations --check --dry-run` → No changes detected
- [x] `python -m pytest` (las únicas fallas son las de PostgreSQL que también fallan en development con SQLite)
- [x] Sin `.env`, llaves ni `prueba.db` en el commit

## Pendiente en otras subtareas

- **ST-214 (José de Jesús):** claim `mfa` y revisarlo en `EsAdministrador`.
- **ST-216 (Isamar):** pruebas de "admin sin 2FA no accede a endpoints de admin" (depende de la ST-214).