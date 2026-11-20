# HU-22 / ST-170 · Investigación y plan de pruebas del historial de accesos

**Subtarea:** ID 170 · [Pruebas] Pruebas
**Historia padre:** HU-22 · Ver mi historial de accesos
**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)
**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa en HU-23, ST-174
**Estado:** Investigación y plan listos. Las pruebas se escriben cuando se integren ST-167, ST-168 y ST-169.

## Descripción

La ST-170 debe probar que **cada inicio de sesión crea un registro** y que **cada usuario solo ve los suyos**. El código que se va a probar (ST-167, ST-168 y ST-169, de Isamar Chávez) todavía no existe en `development`.

Este documento deja lista la parte que no depende de ese código:

1. Qué hay hoy en el proyecto y de qué depende HU-22.
2. Hallazgos de la investigación que afectan cómo se construye HU-22.
3. Recomendaciones para ST-167, ST-168 y ST-169, para que sean fáciles de probar.
4. El plan de pruebas de ST-170: los casos, qué se espera y un ejemplo de cada tipo de prueba.

Los nombres de clases, campos y rutas que aparecen aquí (`RegistroAcceso`, `limpiar_accesos`, etc.) son una **propuesta**. Si Isamar elige otros, las pruebas se ajustan a los suyos.

---

## 1. Criterios de aceptación de HU-22

| # | Criterio | Subtarea que lo implementa |
| --- | --- | --- |
| C1 | Cada login guarda fecha, IP, dispositivo y si fue exitoso | ST-167 (modelo y registro) |
| C2 | `GET /api/v1/auth/accesos/` muestra los últimos 20 con dispositivo legible | ST-168 (endpoint) |
| C3 | Los registros de más de 90 días se borran | ST-169 (limpieza en el worker) |

ST-170 prueba los tres, con énfasis en lo que dice su descripción: *cada login crea registro; solo veo los míos*.

---

## 2. Estado actual del proyecto (development, 19/11/2026)

| Pieza | ¿Existe? | Dónde / Nota |
| --- | --- | --- |
| Endpoint de login | ❌ | `CustomTokenObtainPairSerializer` está en el **PR #38** (ST-81, Danna), sin fusionar. Sin login no hay dónde registrar accesos. |
| Modelo de accesos | ❌ | Lo crea ST-167. |
| Endpoint de historial | ❌ | Lo crea ST-168. `usuarios/urls.py` solo tiene `registro/`. |
| Limpieza de 90 días | ❌ | Lo crea ST-169. |
| Worker | ✅ | `notificaciones/worker.py` + comando `procesar_notificaciones` (T-10/ST-51). Corre cada 5 s y solo procesa notificaciones. |
| IP del cliente | ⚠️ | `comun/eventos.ip_de()` usa solo `REMOTE_ADDR`. No lee `X-Forwarded-For`. |
| django-axes | ✅ | HU-25/ST-183. Ya guarda intentos y accesos en sus propias tablas (ver hallazgo 3.2). |
| Paginación | ❌ global | `REST_FRAMEWORK` no define `DEFAULT_PAGINATION_CLASS`. |
| Zona horaria | ✅ | `TIME_ZONE = "America/Mexico_City"`, `USE_TZ = True`. |
| Fixtures | ✅ | `conftest.py`: `api_client`, `usuario`, `llaves`. `UsuarioFactory` con `PASSWORD_PRUEBA`. |

**Orden recomendado para fusionar:** PR #38 (login) → ST-167 → ST-168 → ST-169 → ST-170.

---

## 3. Hallazgos de la investigación

### 3.1 SimpleJWT no emite la señal `user_logged_in`

Django solo emite `user_logged_in` desde `django.contrib.auth.login()`; `authenticate()` emite `user_login_failed` cuando falla, pero nunca `user_logged_in`. SimpleJWT llama a `authenticate()` y entrega tokens sin pasar por `login()`.

**Consecuencias:**

- Un receptor de `user_logged_in` **nunca se ejecutaría** con nuestro login por JWT. Los **fallidos sí** llegarían por `user_login_failed`.
- **Recomendación para ST-167:** registrar el acceso **explícitamente** en el login (`validate()` de `CustomTokenObtainPairSerializer` o la vista), tanto el exitoso como el fallido. Así no depende de señales y es fácil de probar.
- **Posible efecto en HU-25 (a verificar):** django-axes usa `user_logged_in` para su registro de accesos exitosos y para `AXES_RESET_ON_SUCCESS = True`. Si la señal no se emite, ese reinicio podría no ocurrir. Conviene que quien tenga HU-25 lo confirme con una prueba (login fallido, login exitoso, ¿se borró el `AccessAttempt`?).

### 3.2 django-axes ya tiene un registro de accesos

Axes, ya instalado, guarda `AccessAttempt` (intentos fallidos) y `AccessLog` (accesos), y trae `python manage.py axes_reset_logs (edad)`, que borra los `AccessLog` más viejos que la edad indicada (30 días por defecto).

**¿Reutilizarlo en lugar de crear `RegistroAcceso`?** No lo recomiendo, por lo siguiente:

| | `AccessLog` de axes | `RegistroAcceso` propio |
| --- | --- | --- |
| Accesos exitosos con JWT | Depende de `user_logged_in` (ver 3.1) | Se registra en el login |
| Fallidos en la misma tabla | No (van a `AccessAttempt` / `AccessFailureLog`, desactivado por defecto) | Sí, con `exito=False` |
| Relación con el usuario | Guarda `username` como texto | `ForeignKey` a `Usuario` → filtrar "solo los míos" es directo |
| Dispositivo legible | Solo el user-agent crudo | Campo `dispositivo` ya procesado |
| Control de la limpieza | Comando de axes | Nuestro, probado y dentro del worker |

**Recomendación:** modelo propio. Aun así, sirve tener en cuenta `axes_reset_logs` como referencia de diseño de la limpieza.

### 3.3 IP desde `X-Forwarded-For`: no tomar la primera

El encabezado tiene la forma `cliente, proxy1, proxy2`. **El cliente puede escribirlo**, así que la IP de la izquierda puede ser falsa. Lo seguro es leerlo **de derecha a izquierda**, saltando solo los proxies de confianza, y quedarse con la primera IP que no sea de un proxy propio. Si la petición no viene de un proxy de confianza, se ignora el encabezado y se usa `REMOTE_ADDR`.

**Recomendación para ST-167:**

- Una sola función, por ejemplo `comun.red.ip_cliente(request)`, y que `comun/eventos.ip_de()` la use también, para que la bitácora y el historial muestren la misma IP.
- Configurable: `PROXIES_CONFIABLES` (lista de IPs o redes, por defecto vacía). **Vacía = ignorar `X-Forwarded-For`**, que es lo seguro en desarrollo con Docker sin proxy.
- Validar con `ipaddress.ip_address()` y descartar valores que no sean IP.

### 3.4 Librería `user-agents` para el "dispositivo legible"

- Se instala con `pip install pyyaml ua-parser user-agents`; el análisis real lo hace `ua-parser`.
- Da navegador, sistema operativo y dispositivo, por ejemplo `parse(ua).browser.family` → `'Mobile Safari'`, y `str(parse(ua))` → `"iPhone / iOS 5.1 / Mobile Safari 5.1"`.
- Su última versión es la **2.2.0**. La alternativa es usar `ua-parser` directamente (versión 1.x, más mantenida), con algo más de código.

**Recomendación:**

- Usar `user-agents` y **fijar versiones** en `requirements.txt` (`user-agents`, `ua-parser`, `pyyaml`), como el resto del archivo.
- Guardar **dos campos**: `user_agent` crudo, recortado a un máximo (por ejemplo 255), y `dispositivo` legible, calculado **al guardar**, no en cada consulta.
- Si el user-agent viene vacío o no se reconoce: `dispositivo = "Desconocido"`, sin error. Ojo: con un user-agent vacío, la librería no falla, pero devuelve `"Other / Other / Other"`, así que hay que convertir ese caso a `"Desconocido"` a mano.

Probado con `user-agents 2.2.0` y `ua-parser 1.0.2`:

| User-agent | `str(parse(ua))` |
| --- | --- |
| iPhone con iOS 17 y Safari | `iPhone / iOS 17.0 / Mobile Safari 17.0` |
| Windows 10 con Chrome 120 | `PC / Windows 10 / Chrome 120.0.0` |
| Vacío | `Other / Other / Other` |

### 3.5 Limpieza "una vez al día" en un worker que corre cada 5 segundos

`procesar_notificaciones` repite `procesar_lote()` cada 5 s. Si la limpieza se mete ahí sin control, correría unas 17 000 veces al día.

**Recomendación para ST-169:**

1. **La lógica en una función aparte**, `limpiar_accesos_viejos(dias=90) -> int` (devuelve cuántos borró), fácil de probar sin el bucle.
2. **Un comando** `python manage.py limpiar_accesos [--dias 90]` para correrla a mano o desde cron.
3. **En el worker**, llamarla solo si pasaron 24 h desde la última vez. Guardar la hora de la última limpieza en la base (una fila de control) o usar un `pg_try_advisory_lock`, para que con dos workers no se ejecute dos veces.
4. Borrar **por lotes** si hay muchos registros, y registrar en el log cuántos se borraron.

### 3.6 Paginación de "los últimos 20"

No hay paginación global. **Recomendación para ST-168:**

- Paginación **solo en esa vista**: `PageNumberPagination` con `page_size = 20`, sin permitir que el cliente pida más.
- Orden `-fecha` (más reciente primero) y desempate por `-id`.
- Queryset **siempre** filtrado por `request.user`: `RegistroAcceso.objects.filter(usuario=request.user)`. Nunca recibir el usuario por parámetro.
- `permission_classes`: las de por defecto (exige sesión). Con ST-116 (PR #59), un usuario con contraseña temporal recibirá 403 `debe_cambiar_password`, y eso está bien para este endpoint.

### 3.7 Para que las fechas se puedan probar

- Usar `fecha = models.DateTimeField(default=timezone.now, db_index=True)` **en lugar de `auto_now_add=True`**. Con `auto_now_add`, Django ignora el valor que se le pasa al crear, y las pruebas no podrían fabricar registros de hace 91 días sin trucos.
- Índice compuesto `(usuario, -fecha)` para que el historial del usuario sea rápido.

---

## 4. Modelo propuesto (para ST-167)

```python
class RegistroAcceso(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="accesos",
                                null=True, blank=True)       # null: login fallido con correo que no existe
    correo_intentado = models.CharField(max_length=254, blank=True)
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    dispositivo = models.CharField(max_length=120, blank=True)  # "Chrome 120 / Windows 10 / PC"
    exito = models.BooleanField()

    class Meta:
        ordering = ["-fecha", "-id"]
        indexes = [models.Index(fields=["usuario", "-fecha"], name="acceso_usuario_fecha_idx")]
```

**Decisión pendiente para el equipo:** si el correo no existe, ¿se guarda el intento? (`usuario=None`) Sirve para detectar ataques, pero **nunca debe aparecer en el historial de nadie** y no debe guardar la contraseña escrita.

---

## 5. Plan de pruebas de ST-170

Archivo propuesto: `usuarios/tests/test_historial_accesos.py`, con un `RegistroAccesoFactory` en `usuarios/tests/factories.py`.

### 5.1 Cada login crea registro (ST-167)

| # | Caso | Esperado |
| --- | --- | --- |
| P1 | Login exitoso | 1 registro, `exito=True`, del usuario, `fecha` ≈ ahora |
| P2 | Contraseña incorrecta | 1 registro, `exito=False`, del usuario |
| P3 | Correo que no existe | Según la decisión de §4: sin registro, o con `usuario=None`; nunca visible para nadie |
| P4 | Cuenta pendiente o inactiva | 1 registro `exito=False` (no entregó tokens) |
| P5 | Se guarda la IP (`REMOTE_ADDR`) | `ip` = la de la petición |
| P6 | `X-Forwarded-For` falso sin proxy de confianza | Se ignora → `ip` = `REMOTE_ADDR` |
| P7 | `X-Forwarded-For` desde proxy de confianza | `ip` = la primera no confiable leyendo de derecha a izquierda |
| P8 | User-agent de iPhone, Android y Chrome en Windows | `dispositivo` legible y correcto para cada uno |
| P9 | Sin user-agent, o uno muy largo | `dispositivo="Desconocido"`; `user_agent` recortado, sin error |
| P10 | El registro nunca guarda la contraseña | Ningún campo contiene la contraseña enviada |
| P11 | Varios logins seguidos | Un registro por cada login |

### 5.2 Solo veo los míos (ST-168)

| # | Caso | Esperado |
| --- | --- | --- |
| P12 | Sin token | 401 `no_autenticado` |
| P13 | Con token | 200, solo registros del usuario del token |
| P14 | Otro usuario tiene registros | No aparece **ninguno** de ellos |
| P15 | Intentos con `?usuario=<otro>` o similares | Se ignoran; siguen saliendo solo los míos |
| P16 | 25 registros propios | Página 1 con 20, más recientes primero; `next` apunta a la página 2 con 5 |
| P17 | `?page_size=1000` | Sigue devolviendo 20 |
| P18 | Campos de la respuesta | `fecha`, `ip`, `dispositivo`, `exito`; **no** `user_agent` crudo ni el id del usuario |
| P19 | Contraseña temporal (ST-116) | 403 `debe_cambiar_password` |
| P20 | Sin registros | 200 con lista vacía |

### 5.3 Limpieza de 90 días (ST-169)

| # | Caso | Esperado |
| --- | --- | --- |
| P21 | Registros de hace 89, 90 y 91 días | Se borra solo el de 91; documentar si el de 90 exacto se queda |
| P22 | `limpiar_accesos_viejos()` devuelve el número | Igual al número de registros borrados |
| P23 | Comando `limpiar_accesos --dias 30` | Respeta el parámetro |
| P24 | El worker la llama dos veces el mismo día | Solo limpia la primera vez |
| P25 | Pasadas 24 h | Vuelve a limpiar |
| P26 | No toca otras tablas | Notificaciones y usuarios intactos |

### 5.4 Ejemplos de cómo se verán las pruebas

Se ajustan a los nombres finales de ST-167, ST-168 y ST-169.

```python
# usuarios/tests/test_historial_accesos.py
from datetime import timedelta

import pytest
from django.utils import timezone

from usuarios.models import RegistroAcceso                      # ST-167
from usuarios.tests.factories import PASSWORD_PRUEBA, RegistroAccesoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

URL_LOGIN = "/api/v1/auth/login/"         # confirmar con el PR #38
URL_HISTORIAL = "/api/v1/auth/accesos/"
UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def login(api_client, correo, password, **extra):
    return api_client.post(URL_LOGIN, {"email": correo, "password": password}, format="json", **extra)


# P1, P5, P8: cada login exitoso crea un registro con IP y dispositivo
def test_login_exitoso_crea_registro(api_client, llaves):
    usuario = UsuarioFactory()
    login(api_client, usuario.email, PASSWORD_PRUEBA, REMOTE_ADDR="201.141.10.5", HTTP_USER_AGENT=UA_IPHONE)

    acceso = RegistroAcceso.objects.get(usuario=usuario)
    assert acceso.exito is True
    assert acceso.ip == "201.141.10.5"
    assert "iPhone" in acceso.dispositivo


# P6: un X-Forwarded-For escrito por el cliente no cambia la IP
def test_x_forwarded_for_falso_se_ignora(api_client, llaves, settings):
    settings.PROXIES_CONFIABLES = []
    usuario = UsuarioFactory()
    login(api_client, usuario.email, PASSWORD_PRUEBA, REMOTE_ADDR="201.141.10.5",
          HTTP_X_FORWARDED_FOR="1.2.3.4")

    assert RegistroAcceso.objects.get(usuario=usuario).ip == "201.141.10.5"


# P14: solo veo los míos
def test_solo_veo_mis_accesos(api_client, llaves):
    yo, otro = UsuarioFactory(), UsuarioFactory()
    RegistroAccesoFactory.create_batch(3, usuario=yo)
    RegistroAccesoFactory.create_batch(4, usuario=otro)

    api_client.force_authenticate(yo)
    datos = api_client.get(URL_HISTORIAL).json()

    assert datos["count"] == 3


# P16: últimos 20, más recientes primero
def test_pagina_de_20_mas_recientes_primero(api_client, llaves):
    yo = UsuarioFactory()
    ahora = timezone.now()
    for minutos in range(25):
        RegistroAccesoFactory(usuario=yo, fecha=ahora - timedelta(minutes=minutos))

    api_client.force_authenticate(yo)
    datos = api_client.get(URL_HISTORIAL).json()

    fechas = [r["fecha"] for r in datos["results"]]
    assert len(fechas) == 20
    assert fechas == sorted(fechas, reverse=True)
    assert datos["next"] is not None


# P21: se borra lo de más de 90 días
def test_limpieza_borra_solo_mas_de_90_dias():
    from usuarios.accesos import limpiar_accesos_viejos     # ST-169
    ahora = timezone.now()
    viejo = RegistroAccesoFactory(fecha=ahora - timedelta(days=91))
    reciente = RegistroAccesoFactory(fecha=ahora - timedelta(days=89))

    assert limpiar_accesos_viejos(dias=90) == 1
    assert not RegistroAcceso.objects.filter(pk=viejo.pk).exists()
    assert RegistroAcceso.objects.filter(pk=reciente.pk).exists()
```

Notas:

- `force_authenticate` sirve para probar el endpoint de historial sin pasar por el login. P19 sí necesita un token real con el claim `debe_cambiar_password`, igual que las pruebas de ST-116.
- No hace falta `freezegun`: con `fecha` usando `default=timezone.now` (§3.7), las fechas se fabrican directamente.

---

## 6. Resumen de recomendaciones por subtarea

| Para | Recomendación |
| --- | --- |
| ST-167 | Registrar el acceso de forma explícita en el login, no con `user_logged_in` (§3.1) |
| ST-167 | Modelo propio, no `AccessLog` de axes (§3.2) |
| ST-167 | IP con una función única que lea `X-Forwarded-For` de derecha a izquierda solo detrás de proxies de confianza (§3.3) |
| ST-167 | `user-agents` con versiones fijas; guardar el user-agent crudo y el dispositivo legible (§3.4) |
| ST-167 | `fecha` con `default=timezone.now`, no `auto_now_add`; índice `(usuario, -fecha)` (§3.7) |
| ST-168 | Paginación de 20 solo en la vista, queryset filtrado por `request.user` (§3.6) |
| ST-169 | Función + comando + llamada desde el worker como máximo una vez cada 24 h, segura con varios workers (§3.5) |
| HU-25 | Verificar si `AXES_RESET_ON_SUCCESS` funciona con el login por JWT (§3.1) |
| Equipo | Decidir si se guardan intentos con correos que no existen (§4) |

## 7. Siguientes pasos de ST-170

1. Compartir este documento con Isamar antes de que empiece ST-167, ST-168 y ST-169.
2. Cuando se fusionen, crear `RegistroAccesoFactory` y `usuarios/tests/test_historial_accesos.py` con los casos P1–P26, usando sus nombres reales.
3. Actualizar este documento con los resultados (`pytest -v`).

## Fuentes

- [django-axes · Uso y comandos (`axes_reset_logs`)](https://django-axes.readthedocs.io/en/stable/3_usage.html)
- [django-axes · Configuración (`AXES_DISABLE_ACCESS_LOG`, `AXES_ENABLE_ACCESS_FAILURE_LOG`, handlers)](https://django-axes.readthedocs.io/en/stable/4_configuration.html)
- [Django developers · `user_login_failed` y `user_logged_in` se emiten en niveles distintos](https://groups.google.com/g/django-developers/c/UE00pFVuTEc/m/eriFbgF_AwAJ)
- [SimpleJWT · Settings (`UPDATE_LAST_LOGIN`, `ON_LOGIN_SUCCESS`)](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html)
- [SimpleJWT PR #752 · `user_logged_in` en lugar de `update_last_login` (menciona django-axes)](https://github-users.yhajoa.workers.dev/jazzband/djangorestframework-simplejwt/pull/752)
- [MDN · X-Forwarded-For](https://developer.mozilla.org/docs/Web/HTTP/Headers/X-Forwarded-For)
- [Leer X-Forwarded-For de derecha a izquierda con proxies de confianza](https://pinggy.io/blog/x_forwarded_for_and_forwarded_headers/)
- [user-agents en PyPI](https://pypi.python.org/pypi/user-agents)
- [ua-parser en PyPI](https://pypi.org/p/ua-parser)