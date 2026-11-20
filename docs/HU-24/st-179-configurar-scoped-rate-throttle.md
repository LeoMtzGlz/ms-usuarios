
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
},
```

Las tasas configuradas corresponden a los límites establecidos en la HU-24.

| Scope | Límite | Aplicación prevista |
|---|---|---|
| `login` | 10 solicitudes/minuto | Inicio de sesión |
| `registro` | 5 solicitudes/hora | Registro de usuarios |
| `recuperar` | 3 solicitudes/hora | Recuperación de cuenta |
| `reenviar` | 3 solicitudes/hora | Reenvío de códigos |

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

### 6. Dependencias y alcance

**ST-178 — Configurar caché en base de datos**

La implementación utiliza `DatabaseCache` y `cache_table`, disponibles previamente.

**ST-180 — Crear throttle por cuenta**

El control adicional por cuenta corresponde a otra subtarea. No se implementó en ST-179.

**ST-181 — Pruebas de limitación**

Las pruebas automatizadas de los límites y sus casos de aceptación corresponden a ST-181. La presente subtarea realizó una verificación funcional manual del endpoint de registro.

Los endpoints de login, recuperación y reenvío deberán incorporar sus scopes correspondientes cuando estén implementados e integrados.

### 7. Resultado

Se configuró `ScopedRateThrottle` en Django REST Framework, se definieron las tasas previstas para los endpoints públicos y se habilitó el scope `registro`.

Se comprobó su funcionamiento mediante solicitudes HTTP, obteniendo la respuesta `429 Too Many Requests` y el encabezado `Retry-After` al superar el límite configurado.

La implementación conserva la configuración de caché existente y respeta el alcance de las subtareas relacionadas.

**Responsable de la actividad:** Claudia Maritza Santibáñez García (l22420423).