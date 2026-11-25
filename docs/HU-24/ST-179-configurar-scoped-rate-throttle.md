
# HU-24 — Limitar las solicitudes a los endpoints públicos

## ST-179. Configurar ScopedRateThrottle por endpoint

**Estado:** Completada
**Responsable:** Claudia Maritza Santibáñez García (l22420423)

### 1. Descripción

Se implementó la configuración de `ScopedRateThrottle` de Django REST Framework (DRF) para establecer límites de solicitudes por endpoint en el microservicio `ms-usuarios`.

Esta configuración utiliza la caché de PostgreSQL implementada en la ST-178 y permite restringir las solicitudes realizadas por un mismo cliente, con el objetivo de reducir el abuso de los endpoints públicos.

### 2. Configuración de throttling

En `config/settings.py`, dentro del diccionario existente `REST_FRAMEWORK`, se agregaron las siguientes propiedades:

```python
# t-24/st-179: Limitación de solicitudes por endpoint
"DEFAULT_THROTTLE_CLASSES": (
    "rest_framework.throttling.ScopedRateThrottle",
),
"DEFAULT_THROTTLE_RATES": {
    "login": "10/min",
    "registro": "5/hour",
    "recuperar": "3/hour",
    "reenviar": "3/hour",
    "cuenta": "3/hour",
},

# t-24/st-179: Utilizar REMOTE_ADDR para identificar al cliente
"NUM_PROXIES": 0,
```

Las tasas configuradas corresponden a los límites establecidos en la HU-24.

| Scope | Límite | Aplicación prevista |
|---|---|---|
| `login` | 10 solicitudes/minuto | Inicio de sesión |
| `registro` | 5 solicitudes/hora | Registro de usuarios |
| `recuperar` | 3 solicitudes/hora | Recuperación de cuenta |
| `reenviar` | 3 solicitudes/hora | Reenvío de códigos |
| `cuenta` | 3 solicitudes/hora | Limitación por cuenta, ST-180 |

### Identificación de la dirección IP

Se configuró `NUM_PROXIES = 0` en Django REST Framework para utilizar `REMOTE_ADDR` al identificar al cliente.

Esta configuración evita que un cliente pueda modificar su identificador de throttling mediante valores arbitrarios de la cabecera `X-Forwarded-For`.

Se comprobó que dos solicitudes con la misma dirección `REMOTE_ADDR`, pero diferentes valores de `X-Forwarded-For`, conservan el mismo identificador.

**Consideración de despliegue:** esta configuración supone que `REMOTE_ADDR` contiene la dirección que se desea limitar. Si posteriormente se utiliza un proxy inverso, deberá revisarse la identificación de IP para evitar que todos los clientes compartan el contador del proxy.

La definición de una tasa no activa por sí sola el límite en una vista. Es necesario asignar el atributo `throttle_scope` correspondiente.

### 3. Configuración de caché

La limitación utiliza la caché predeterminada configurada previamente en PostgreSQL mediante `DatabaseCache`.

Configuración existente en `config/settings.py`:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}
```

### Creación automática de `cache_table`

Se identificó que `DatabaseCache` requiere la tabla `cache_table`, la cual no se crea automáticamente mediante las migraciones habituales de Django.

Para garantizar su disponibilidad se realizaron los siguientes cambios:

- **Dockerfile:** se agregó `python manage.py createcachetable` después de `migrate` y antes de iniciar el servidor.
- **GitHub Actions:** se incorporó un paso para ejecutar `python manage.py createcachetable` después de aplicar las migraciones y antes de ejecutar pytest.

El comando puede ejecutarse nuevamente cuando la tabla ya existe, sin eliminar su contenido.

Estos cambios permiten preparar la caché en entornos nuevos, evitando errores del endpoint de registro derivados de la ausencia de `cache_table`.

Se verificó que la tabla `cache_table` existe en PostgreSQL.

No se realizaron modificaciones a la configuración de caché correspondiente a ST-178.

### 4. Aplicación al endpoint de registro

En `usuarios/views.py`, dentro de `RegistroView`, se agregó:

```python
# t-24/st-179: Limitar el registro a 5 solicitudes por hora por IP
throttle_scope = "registro"
```

La vista conserva sus permisos, autenticación y lógica de registro originales.

El scope `registro` utiliza la tasa `5/hour`, limitando las solicitudes desde una misma IP según la identificación de cliente utilizada por DRF.

Los demás scopes quedaron definidos en la configuración global, pero todavía requieren su asignación a los endpoints correspondientes cuando estos estén disponibles.

### 5. Verificaciones realizadas

#### 5.1. Configuración de Django REST Framework

Se verificó que DRF reconoce correctamente:

- Scope: `registro`.
- Clase de throttling: `ScopedRateThrottle`.
- Tasa configurada: `5/hour`.

#### 5.2. Disponibilidad de caché

Se comprobó mediante Django que la tabla `cache_table` existe en PostgreSQL.

**Resultado:** `cache_table existe: True`.

#### 5.3. Prueba funcional del endpoint

Se realizaron seis solicitudes consecutivas al endpoint:

`POST /api/v1/auth/registro/`

Las solicitudes utilizaron datos vacíos y una IP reservada para pruebas, evitando la creación de usuarios.

| Solicitud | Código HTTP | Resultado |
|---|---|---|
| 1 | 400 | Validación de datos |
| 2 | 400 | Validación de datos |
| 3 | 400 | Validación de datos |
| 4 | 400 | Validación de datos |
| 5 | 400 | Validación de datos |
| 6 | 429 | Límite de solicitudes alcanzado |

La sexta solicitud devolvió:

```text
Retry-After: 3600
```

El encabezado indica el tiempo de espera en segundos.

El contador utilizado durante la prueba se eliminó al finalizar, sin modificar los registros de usuarios.

#### 5.4. Verificaciones automatizadas

Se ejecutaron las comprobaciones de calidad establecidas para el proyecto:

| Comprobación | Resultado |
|---|---|
| `python -m ruff check .` | Sin errores |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python -m pytest -q` | 259 pruebas exitosas |
| `git diff --check` | Sin errores |

La ejecución de pytest finalizó con **259 pruebas correctas en 32.46 segundos**.

No se detectaron fallos en las pruebas existentes después de incorporar la configuración de `ScopedRateThrottle`.

#### 5.5. Prueba automatizada del límite de registro

Se agregó el archivo:

`usuarios/tests/test_throttle_registro.py`

La prueba `test_sexta_solicitud_de_registro_responde_429` verifica el comportamiento del endpoint:

`POST /api/v1/auth/registro/`

| Solicitudes | Código HTTP | Comportamiento |
|---|---|---|
| 1 a 5 | 400 | La petición llega a la validación de datos |
| 6 | 429 | Se alcanza el límite de solicitudes |

Adicionalmente, la prueba comprueba que:

- Las solicitudes utilizan la misma dirección `REMOTE_ADDR`.
- Cambiar la cabecera `X-Forwarded-For` no permite evadir el límite.
- La respuesta HTTP 429 incluye el encabezado `Retry-After`.
- Los contadores se aíslan mediante `LocMemCache`, evitando interferencias con otras pruebas.
- No se crean usuarios, ya que se utilizan datos de registro vacíos.

**Comando de ejecución:**

```powershell
python -m pytest usuarios/tests/test_throttle_registro.py -v
```

**Resultado:** 1 prueba exitosa.

#### 5.6. Prueba funcional del límite de login

Se aplicó el scope `login` a `CustomTokenObtainPairView`, correspondiente al endpoint:

`POST /api/v1/auth/login/`

La configuración establece un máximo de **10 solicitudes por minuto por IP**.

Se ejecutaron 11 solicitudes consecutivas utilizando una dirección IP reservada para pruebas y credenciales inválidas.

| Comprobación | Resultado |
|---|---|
| Scope aplicado | `login` |
| Tasa configurada | `10/min` |
| Identificación de IP | `NUM_PROXIES = 0` |
| Solicitudes 5–10 | HTTP 403 por bloqueo de `django-axes` |
| Solicitud 11 | HTTP 429 — Too Many Requests |
| Encabezado `Retry-After` | 58 segundos |

**Interacción con `django-axes`:**

Durante la prueba, `django-axes` bloqueó los intentos repetidos de autenticación mediante respuestas HTTP 403.

Sin embargo, `ScopedRateThrottle` continuó contabilizando las solicitudes y devolvió HTTP 429 al alcanzar el límite configurado.

Ambas protecciones permanecieron habilitadas.

El contador temporal del throttle se eliminó al finalizar la prueba.

### 6. Dependencias y alcance

**ST-178 — Configurar caché en base de datos**

La implementación utiliza `DatabaseCache` y `cache_table`, disponibles previamente.

**ST-180 — Crear throttle por cuenta**

El control adicional por cuenta corresponde a otra subtarea. No se implementó en ST-179.

**ST-181 — Pruebas de limitación**

Se incorporó en ST-179 una prueba automatizada específica del límite
de registro, solicitada durante la revisión del PR #74.

Las pruebas adicionales de login, recuperación, reenvío y limitación
por cuenta corresponden a ST-181, desarrollada por otro integrante.

### 7. Resultado

Se configuró `ScopedRateThrottle` en Django REST Framework para establecer límites por endpoint.

Se habilitaron y verificaron los siguientes scopes:

| Endpoint | Scope | Límite |
|---|---|---|
| `POST /api/v1/auth/registro/` | `registro` | 5 solicitudes/hora por IP |
| `POST /api/v1/auth/login/` | `login` | 10 solicitudes/minuto por IP |

Se incorporó el scope `cuenta` con una tasa de `3/hour` para su integración con ST-180.

Se configuró `NUM_PROXIES = 0` para impedir que los clientes evadan los límites modificando la cabecera `X-Forwarded-For`.

También se incorporó la creación automática de `cache_table` en Docker y GitHub Actions.

Se agregó una prueba automatizada que comprueba que la sexta solicitud de registro responde HTTP 429.

Las pruebas funcionales verificaron las respuestas HTTP 429 y el encabezado `Retry-After` en los endpoints de registro y login.

Los scopes `recuperar` y `reenviar` permanecen configurados y deberán asociarse a sus respectivos endpoints cuando estén disponibles.