# HU-22 / ST-167 · Crear el modelo RegistroAcceso y llenarlo en cada login

**Subtarea:** ID 167 · [Backend] Crear el modelo RegistroAcceso y llenarlo en cada login
**Historia:** HU-22 · Ver mi historial de accesos
**Responsable:** Isamar Chávez Díaz (chamar29) · **Revisa:** Isis Vázquez (isis0015)
**Estado:** En revisión

## Descripción

Cada intento de login a una cuenta que existe guarda un `RegistroAcceso` con **fecha, IP,
dispositivo y si fue exitoso** (primer criterio de HU-22). Lo usan después el endpoint de
historial (ST-168) y la limpieza de 90 días (ST-169).

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `usuarios/models.py` | Modelo `RegistroAcceso` (bloque `# t-22/st-167`) |
| `usuarios/migrations/0005_registroacceso.py` | Generada con `makemigrations` |
| `usuarios/accesos.py` | `ip_del_request`, `dispositivo_legible`, `buscar_usuario`, `registrar_acceso` |
| `usuarios/tokens.py` | El login de la ST-81 llama a `registrar_acceso` (líneas marcadas `# t-22/st-167`) |
| `requirements.txt` | `user-agents==2.2.0` |
| `config/settings.py` y `.env.example` | `PROXIES_CONFIABLES` (bloque `# t-22/st-167`) |
| `usuarios/tests/test_registro_acceso.py` | 18 pruebas |

## Modelo

| Campo | Tipo | Ejemplo |
| --- | --- | --- |
| `usuario` | FK a Usuario (`related_name="accesos"`) | — |
| `fecha` | fecha y hora, automática | `2026-11-19 08:30` |
| `ip` | IP (puede ser nula) | `200.1.2.3` |
| `dispositivo` | texto legible | `Chrome 131 en Windows 10` |
| `user_agent` | texto original (máx. 500) | `Mozilla/5.0 (Windows NT 10.0; ...)` |
| `exitoso` | sí / no | `True` |

Orden por defecto: del más reciente al más antiguo. Índice por `(usuario, -fecha)` para el historial.

## Cuándo se guarda

| Caso en el login | ¿Se guarda? | `exitoso` |
| --- | --- | --- |
| Login correcto | Sí | `True` |
| Contraseña incorrecta en una cuenta que existe | Sí | `False` |
| Cuenta pendiente o inactiva | Sí | `False` |
| Correo o teléfono que no existe | **No** (no hay a quién mostrárselo) | — |

- **IP:** `REMOTE_ADDR`. Solo si la petición viene de un proxy de `PROXIES_CONFIABLES` se lee
  `X-Forwarded-For` **de derecha a izquierda**, saltando esos proxies, y se toma la primera IP que no
  sea de ellos. Un valor que no es una IP válida se descarta: nunca rompe el login.
  (Corrección de la revisión de Isis: `X-Forwarded-For` lo puede escribir cualquier cliente.)
- **Dispositivo:** se arma con la librería `user-agents`; si no se reconoce, `Desconocido`.

## Cómo probarlo

```powershell
docker compose build
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest usuarios/tests/test_registro_acceso.py -v
```

Resultado: 18 pruebas en verde; `ruff` y `makemigrations --check` limpios.

## Pendiente (otras subtareas)

- **ST-168:** `GET /api/v1/auth/accesos/` con los últimos 20 de la persona.
- **ST-169:** borrar los registros de más de 90 días desde el worker.