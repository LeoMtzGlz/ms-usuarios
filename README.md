# svc-usuarios

Microservicio de usuarios del proyecto del grupo, hecho con **Django REST Framework** y **PostgreSQL**. Cuando esté completo se encargará del registro, la activación por código, el inicio de sesión con JWT, la recuperación de contraseña, los roles, la administración de cuentas y los avisos por correo y WhatsApp. Los demás microservicios (catálogo, pedidos...) confiarán en él para saber quién es cada persona.

El trabajo se organiza con Scrum: cada tarea e historia del backlog de Jira entra en su propio commit, con su clave al inicio del mensaje (`T-02: ...`).

---

## Estado del proyecto

Ya está lista la **base técnica**: el proyecto, las pruebas automáticas, el modelo de usuario y el formato de errores. Todavía no hay endpoints de registro ni de sesión; esos llegan con las historias de usuario.

| Orden | Tarea | Qué aporta | Estado |
| --- | --- | --- | --- |
| 1 | **T-01** · Crear el proyecto DRF con PostgreSQL y Docker Compose | Proyecto `config/`, apps `comun`, `usuarios` y `notificaciones`; endpoint de salud; contenedores | Terminada |
| 2 | **T-06** · Configurar pruebas automáticas e integración continua | pytest, factory_boy, ruff y GitHub Actions | Terminada |
| 3 | **T-02** · Crear el modelo de usuario en PostgreSQL | Modelo `Usuario` con correo como identificador, teléfono E.164, rol y estado | Terminada |
| 4 | **T-03** · Definir el formato estándar de errores y el registro de eventos | Respuestas de error `{codigo, mensaje, campos}` y `registrar_evento()` | Terminada |
| 5 | **T-04** · Generar las llaves RS256 y configurar SimpleJWT | Tokens de sesión | Siguiente |

> T-06 va antes que T-02 porque las pruebas del modelo usan pytest y factory_boy.

Durante la verificación inicial de la ST-31 se ejecutaron **137 pruebas** exitosas, tanto localmente como mediante Docker. Después de actualizar la rama con `development`, se verificaron **189 pruebas exitosas** en el entorno local.

Para consultar los procedimientos de ejecución, configuración y solución de problemas, revisa la [guía de ejecución de pruebas](docs/T-06/ST-31-documentar-pruebas.md).

---

## Requisitos

- **Docker Desktop** (o Docker Engine con Docker Compose). Es lo único indispensable.
- **Git**.
- Opcional, para trabajar sin Docker: **Python 3.12** y **PostgreSQL 16**.

## Arranque desde cero

```bash
git clone <url-del-repositorio>
cd svc-usuarios
cp .env.example .env           # ajusta SECRET_KEY; .env nunca se sube
docker compose up --build      # levanta PostgreSQL 16 y la API en http://localhost:8000
```

En otra terminal, comprueba que todo responde:

```bash
curl http://localhost:8000/api/v1/salud/
# {"estado":"ok","bd":"ok"}
```

Crea un superusuario para entrar al admin de Django en <http://localhost:8000/admin/>. Pide **correo** y contraseña, no un nombre de usuario:

```bash
docker compose exec api python manage.py createsuperuser
```

> **¿Ya tenías la base de T-01?** El modelo de usuario propio exige una base vacía. Si al arrancar aparece `InconsistentMigrationHistory`, borra la base y vuelve a levantar: `docker compose down -v && docker compose up --build`.

## Variables de entorno

Se leen del archivo `.env` (copia de `.env.example`).

| Variable | Ejemplo | Para qué |
| --- | --- | --- |
| `DEBUG` | `True` | `True` en tu máquina; `False` en pruebas, demo y producción |
| `SECRET_KEY` | una cadena larga y aleatoria | Firma interna de Django. Si falta, Django no arranca, a propósito |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Nombres de host que la API acepta |
| `DATABASE_URL` | `postgres://svc:svc@db:5432/svc_usuarios` | Conexión a PostgreSQL. Dentro de Docker el host es `db`, no `localhost` |
| `LOG_LEVEL` | `INFO` | Opcional. Nivel de los logs `svc.*` |

---

## Estructura

```text
svc-usuarios/
├── config/                 # proyecto: settings, urls y wsgi
├── comun/                  # lo compartido por todas las apps
│   ├── views.py            #   GET /api/v1/salud/
│   ├── errores.py          #   catálogo de errores y manejador de excepciones
│   ├── eventos.py          #   registrar_evento(): la bitácora de auditoría
│   └── tests/
├── usuarios/               # cuentas de usuario
│   ├── models.py           #   modelo Usuario y cambiar_estado()
│   ├── managers.py         #   create_user y create_superuser
│   ├── telefono.py         #   normalización a E.164
│   ├── admin.py            #   pantalla de usuarios del admin
│   ├── migrations/
│   └── tests/              #   factories.py y pruebas del modelo y del admin
├── notificaciones/         # bandeja de salida y canales (llega en T-07)
├── docs/
│   ├── catalogo-errores.md # todos los códigos de error de la API
│   └── tareas/             # una ficha de conceptos por tarea
├── .github/workflows/ci.yml
├── docker-compose.yml · Dockerfile
├── requirements.txt · requirements-dev.txt
└── pytest.ini · pyproject.toml
```

Por qué tres apps: `config/` es el proyecto y cada app agrupa un tema (es la convención de Django), con lo que cada escuadra trabaja en su parte. `notificaciones` está separada porque podría volverse su propio servicio más adelante.

---

## Lo que ya hace la API

### Matriz endpoint × rol (HU-13 / ST-127)

La columna **Estado** evita confundir las rutas que ya existen en `development` con las que todavía están en un PR,
en una rama o en el backlog. Una ruta pública puede usarse sin token y, por lo tanto, también por cualquier rol.

| Método | Ruta | Estado | Sin token | Cliente | Operativo | Administrador | Permiso esperado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/api/v1/salud/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/registro/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `GET` | `/api/schema/` | Disponible | Sí | Sí | Sí | Sí | Pública (`drf-spectacular`) |
| `GET` | `/api/docs/` | Disponible | Sí | Sí | Sí | Sí | Pública (`drf-spectacular`) |
| `GET`, `POST` | `/admin/` y sus rutas internas | Disponible | No | No¹ | No¹ | No¹ | Autenticación de Django |
| `POST` | `/api/v1/auth/login/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/google/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `GET` | `/api/v1/auth/privacidad/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/privacidad/aceptar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` |
| `POST` | `/api/v1/auth/2fa/activar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` |
| `POST` | `/api/v1/auth/2fa/confirmar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` |
| `POST` | `/api/v1/auth/2fa/desactivar/` | Disponible | No | Sí | Sí | No | `IsAuthenticated` + `ContrasenaDefinitiva` |
| `POST` | `/api/v1/auth/activar/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/reenviar-codigo/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/token/renovar/` | Disponible | Sí² | Sí | Sí | Sí | `AllowAny` + token de renovación válido |
| `POST` | `/api/v1/auth/logout/` | Planeado (HU-08) | No | Sí | Sí | Sí | `IsAuthenticated` |
| `POST` | `/api/v1/auth/logout-todo/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` |
| `POST` | `/api/v1/auth/recuperar/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/restablecer/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `POST` | `/api/v1/auth/cambiar-password/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` (exenta de `ContrasenaDefinitiva`) |
| `GET` | `/api/v1/auth/llave-publica/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` |
| `GET`, `PATCH` | `/api/v1/auth/perfil/` | Disponible | No | Sí | Sí | Sí | Propietario autenticado |
| `GET` | `/api/v1/auth/accesos/` | Disponible | No | Sí | Sí | Sí | Propietario autenticado |
| `POST` | `/api/v1/auth/eliminar-cuenta/` | Planeado (ST-174) | No | Sí | Sí | Sí³ | Propietario autenticado |
| `GET`, `POST` | `/api/v1/usuarios/` | Disponible | No | No | No | Sí | `EsAdministrador` |
| `PATCH` | `/api/v1/usuarios/{id}/` | Disponible | No | No | No | Sí | `EsAdministrador` |
| `POST` | `/api/v1/usuarios/{id}/desactivar/` | Disponible | No | No | No | Sí | `EsAdministrador` |
| `POST` | `/api/v1/usuarios/{id}/reactivar/` | Disponible | No | No | No | Sí | `EsAdministrador` |
| `PATCH` | `/api/v1/usuarios/{id}/rol/` | Planeado (ST-131) | No | No | No | Sí | `EsAdministrador` |
| `GET` | `/api/v1/auditoria/` | Disponible | No | No | No | Sí | `EsAdministrador` |

¹ El campo `rol` de `Usuario` no concede acceso al administrador de Django. `/admin/` exige una cuenta con
`is_staff=True`; las cuentas creadas con `createsuperuser` tienen además `is_superuser=True`.

² La renovación no usa un token de acceso en el encabezado, pero sí exige un token de renovación válido en la petición.

³ El único administrador del sistema no puede eliminar su propia cuenta, según HU-23.

Para los endpoints de DRF, cualquier vista que no declare permisos hereda `IsAuthenticated`. ST-128 aplicará las
clases de `comun/permisos.py` cuando una ruta necesite restringirse a un rol concreto o al dueño del recurso.
La prueba `test_todo_metodo_api_esta_en_la_matriz_de_autorizacion` de
[`usuarios/tests/test_autorizacion_endpoints.py`](usuarios/tests/test_autorizacion_endpoints.py) falla si se agrega
una combinación de ruta y método HTTP bajo `/api/` sin clasificarla en la matriz ejecutable de ST-129.
Las rutas de historias que todavía no fijan una URL se registran en
[`docs/HU-13/ST-127-matriz-endpoint-rol.md`](docs/HU-13/ST-127-matriz-endpoint-rol.md) y se agregarán a esta tabla
cuando el equipo confirme su contrato.

### El modelo `Usuario` (T-02)

- Se entra con el **correo**, que es único sin importar mayúsculas: la restricción `email_unico_ci` vive en PostgreSQL.
- El **teléfono** es opcional, único y se guarda en formato E.164 (`+524431234567`).
- La llave primaria es un **UUID**.
- Campos del backlog: `rol` (cliente, operativo, administrador), `estado` (pendiente, activo, inactivo), `canal_preferido` (correo, WhatsApp), `email_verificado`, `telefono_verificado`, `debe_cambiar_password`, `token_version`, `acepto_privacidad_en` y `version_privacidad`.
- Una cuenta nueva es cliente, pendiente y con `token_version = 0`.

> **Regla:** solo `usuario.cambiar_estado(nuevo)` modifica `estado`, `is_active` y `token_version`. Ninguna vista los asigna directamente. Al desactivar, `token_version` sube y se cierran todas las sesiones.

### Datos al eliminar una cuenta (HU-23 / ST-172)

Al eliminar una cuenta (`POST /api/v1/auth/eliminar-cuenta/`, ST-174) el usuario **no se borra**: se **anonimiza**, para que
el sistema deje de tener sus datos personales y los registros relacionados sigan siendo consistentes.

| Dato | Acción | Después de eliminar |
| --- | --- | --- |
| Nombre y apellidos | Anonimizar | `Usuario` `eliminado` |
| Correo | Anonimizar | `eliminado-<id>@anonimo.invalid` |
| Teléfono | Anonimizar | vacío (`NULL`) |
| Contraseña | Anonimizar | inutilizable (`set_unusable_password()`) |
| Estado y sesiones | Cambiar | `inactivo`, `token_version + 1` y refresh tokens en lista negra |
| `id`, `rol`, fechas, aceptación de privacidad | Conservar | igual |
| Códigos de verificación, 2FA, notificaciones pendientes | Borrar | — |
| Historial de accesos (HU-22) y bitácora (HU-26) | Conservar | igual |
| Notificaciones ya enviadas | Conservar | sin el contenido del mensaje (`contexto` vacío) |
| Intentos de login de django-axes | Borrar | guardan el correo en texto |

El detalle campo por campo, el orden de los pasos y los puntos que se acuerdan con los otros módulos están en
[`docs/HU-23/st-172-datos-anonimizados.md`](docs/HU-23/st-172-datos-anonimizados.md).

### Formato de errores (T-03)

Todo error de la API responde con la misma forma:

```json
{"codigo": "datos_invalidos", "mensaje": "Revisa los datos enviados.", "campos": {"correo": ["Introduzca una dirección de correo electrónico válida."]}}
```

- `codigo`: identificador estable; el frontend decide con él qué hacer.
- `mensaje`: texto en español para mostrar a la persona.
- `campos`: solo en errores de validación.

Con `DEBUG=False` nunca se muestra un stacktrace: el detalle queda en el log y el cliente recibe `error_interno`. La lista completa de códigos y qué debe hacer el frontend con cada uno está en [`docs/catalogo-errores.md`](docs/catalogo-errores.md).

Para responder un error en una vista **no se arma la respuesta a mano**: se lanza la excepción del catálogo.

```python
from comun.errores import CuentaPendiente

raise CuentaPendiente()   # 403 {"codigo": "cuenta_pendiente", ...}
```

### Bitácora de eventos (T-03)

`registrar_evento(accion, usuario=None, request=None, resultado="ok", **detalles)` es la única puerta a la bitácora. Escribe una línea JSON en el log `svc.auditoria` y (HU-26 / ST-188) guarda además el evento en la tabla `EventoAuditoria`, con usuario, IP, user agent y `detalles`. Si el guardado falla, el error queda en el log y el flujo que la llamó sigue. Las claves sensibles (`password`, `codigo`, `token`...) se guardan como `***` a cualquier profundidad. Un administrador consulta la tabla en `GET /api/v1/auditoria/` (ST-189, [documentación](docs/HU-26/ST-189-endpoint-auditoria.md)). Los flujos que aún no registran su evento están en [`docs/HU-26`](docs/HU-26/ST-190-pruebas-bitacora.md).

```python
from comun.eventos import registrar_evento

registrar_evento("login_fallido", usuario, request, resultado="error", motivo="credenciales")
```

### Política de contraseñas (T-12)
<!-- t-12/st-105 -->

Se aplica con `validate_password()` en el registro (`usuarios/serializers.py`). Recuperación, cambio de contraseña y contraseñas temporales la usarán al integrarse (HU-10, HU-11 y HU-15).

| Regla | Implementación (`AUTH_PASSWORD_VALIDATORS` en `config/settings.py`) |
|---|---|
| Mínimo 8 caracteres | `MinimumLengthValidator` con `min_length=8` |
| Al menos una mayúscula y un número | `comun.validadores.MayusculaYNumeroValidator` |
| No es una contraseña común | `CommonPasswordValidator` |
| No se parece al correo ni al nombre | `UserAttributeSimilarityValidator` (`email`, `first_name`, `last_name`) |

Una contraseña de solo números también se rechaza, porque no tiene mayúscula.

Los mensajes de error están en español y siguen el formato de `comun/errores.py`. Ejemplo de respuesta 400:

```json
{
  "codigo": "datos_invalidos",
  "mensaje": "Revisa los datos enviados.",
  "campos": {
    "password": [
      "La contraseña debe incluir al menos una letra mayúscula.",
      "La contraseña debe incluir al menos un número."
    ]
  }
}
```

#### Almacenamiento
- Las contraseñas se guardan con **Argon2id** (`argon2-cffi`), configurado en `PASSWORD_HASHERS`. **Nunca** en texto plano.
- **PBKDF2** queda como respaldo: un hash antiguo sigue funcionando y se convierte a Argon2 la siguiente vez que se verifica la contraseña.
- `registrar_evento()` (`comun/eventos.py`) oculta con `***` cualquier detalle cuya clave contenga `password`, `codigo`, `token` o `secreto`, así que no llegan a la bitácora.

#### Cómo cambiar la política
1. Edita `AUTH_PASSWORD_VALIDATORS` en `config/settings.py`.
2. Actualiza `AYUDA_POLITICA_PASSWORD` en `comun/validadores.py`.
3. Actualiza esta sección y corre `pytest comun/tests/test_validadores.py comun/tests/test_hash_password.py`.

---

## Pruebas y calidad

```bash
docker compose run --rm api pytest              # ejecuta todas las pruebas contra PostgreSQL
docker compose run --rm api pytest usuarios -v  # solo una app, con detalle
docker compose run --rm api ruff check .        # estilo
docker compose run --rm api python manage.py makemigrations --check --dry-run  # que no falten migraciones
```

Sin Docker, con **Python 3.12**, un PostgreSQL local y las variables de `.env` exportadas:

```bash
pip install -r requirements.txt
pytest
```

El paso a paso sin Docker está en [`docs/T-06/ST-31-documentar-pruebas.md`](docs/T-06/ST-31-documentar-pruebas.md).

**GitHub Actions** corre en cada push y en cada Pull Request hacia `development` y `main`: estilo con ruff, revisión de que no falten migraciones (`makemigrations --check --dry-run`) y pruebas contra PostgreSQL 16. El check obligatorio se llama **`pruebas`**; además del CI en verde, un Pull Request necesita **1 aprobación** para fusionarse. Detalle en [`docs/T-06/ST-29-workflow-github-actions.md`](docs/T-06/ST-29-workflow-github-actions.md) y [`docs/T-06/ST-30-proteger-rama-principal.md`](docs/T-06/ST-30-proteger-rama-principal.md).

Cómo están organizadas las pruebas:

- Cada app tiene su carpeta `tests/`, con un archivo por tema: `test_modelo.py`, `test_errores.py`...
- `usuarios/tests/factories.py` fabrica usuarios válidos: `UsuarioFactory(rol=Rol.ADMINISTRADOR)`. Su contraseña es `PASSWORD_PRUEBA` (`Secreta123`).
- `conftest.py`, en la raíz, tiene fixtures que cualquier prueba puede pedir como parámetro: `api_client` (cliente de DRF), `usuario` (usuario activo con `PASSWORD_PRUEBA`) y `llaves` (par de llaves RS256 temporal para firmar tokens sin `llaves/*.pem`).
- pytest-django corre las pruebas con `DEBUG=False`, como en producción.

---

## Comandos frecuentes

| Para | Comando |
| --- | --- |
| Ver los logs de la API | `docker compose logs -f api` |
| Levantar, ver y detener el worker de notificaciones | `docker compose up -d worker`, `docker compose logs -f worker`, `docker compose stop worker` (varios: `docker compose up -d --scale worker=2`; si la base es nueva, levanta antes `api` para que migre) |
| Abrir un shell de Django | `docker compose exec api python manage.py shell` |
| Crear una migración | `docker compose run --rm api python manage.py makemigrations usuarios` |
| Aplicar migraciones | `docker compose exec api python manage.py migrate` |
| Entrar a PostgreSQL | `docker compose exec db psql -U ms_user -d ms_usuarios` |
| Ver la tabla de usuarios | `docker compose exec db psql -U ms_user -d ms_usuarios -c "\d usuarios_usuario"` |
| Reconstruir tras cambiar dependencias | `docker compose build` |
| Borrar la base y empezar de cero | `docker compose down -v` |

---

## Cómo trabajamos en equipo

Somos varias personas en un solo repositorio. Estas reglas evitan casi todos los conflictos.

1. **Nadie crea carpetas personales.** El código se acomoda por funcionalidad, no por persona. Quién hizo qué ya lo registran Jira y GitHub.
2. **`development` y `main` están protegidas** (ruleset `proteccion-ramas`). Todo entra por Pull Request hacia `development`, con el check `pruebas` en verde y 1 aprobación. `development` pasa a `main` con un Pull Request al cierre de cada sprint.
3. **Una rama por subtarea, con el formato `t-XX/st-YY`:** `XX` es el número de la tarea o historia (T-04 → `t-04`, HU-28 → `t-28`) y `YY` el ID de la subtarea. Ejemplo: `git switch -c t-07/st-89`. Que dure uno o dos días.
4. **Sincroniza cada mañana:** `git pull origin development` dentro de tu rama.
5. **Commits pequeños, con la clave al inicio en el mismo formato:** `t-07/st-89: Activar la lista negra de SimpleJWT`.
6. **Cada escuadra trabaja en sus archivos**, y cada quien escribe sus pruebas en su propio archivo (`usuarios/tests/test_registro.py`).
7. **Si tu PR toca `config/`, `usuarios/models.py` o migraciones**, pide también la revisión del profesor.
8. **Las migraciones no se editan a mano.** Si chocan con las de otra rama, borra la tuya, trae `development` y vuelve a correr `makemigrations`.
9. **Revisa quien continúa tu trabajo** (backlog v3): la siguiente subtarea de la misma historia; si no hay, la primera de la historia que tu subtarea bloquea; si no, la siguiente historia de la épica; al final de la épica, quien te entregó. Nadie revisa su propio trabajo. El revisor se pide en *Reviewers* al abrir el Pull Request. **El revisor aprueba o pide cambios; el autor fusiona su propio PR** con **Create a merge commit**. Si ya aprobaste, avísale al autor, no lo fusiones tú.

**Una subtarea está terminada (Definition of Done)** cuando su Pull Request está fusionado en `development`, el CI está en verde, lo aprobó su revisor, tiene pruebas y documentación en `docs/`, y la subtarea está en *Finalizada* en Jira con el enlace al PR.

## Convenciones de código

- Nombres del dominio en **español** (`Usuario`, `cambiar_estado`, `registrar_evento`); lo del framework se queda como es (`get`, `save`, `objects`).
- Estilo con **ruff**, líneas de hasta 120 caracteres.
- **Errores:** se lanza la excepción del catálogo; un código nuevo se agrega en `comun/errores.py` y en `docs/catalogo-errores.md` en el mismo Pull Request.
- **Bitácora:** las acciones importantes llaman a `registrar_evento()`. Nunca se registra `request.data` completo.
- **Secretos:** nunca en el código ni en Git. Van en `.env`, y `.env.example` lleva solo nombres y valores de ejemplo.

---

## Problemas comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `could not translate host name "db"` | Corriste Django fuera de Docker | Usa Docker, o pon `localhost` en tu `.env` local |
| `connection refused` al arrancar | La API arrancó antes que PostgreSQL | Revisa `healthcheck` y `depends_on` en `docker-compose.yml` |
| `InconsistentMigrationHistory` | La base tiene migraciones de antes del usuario propio | `docker compose down -v` y levantar de nuevo |
| `Dependency on app with no migrations: usuarios` | Falta la migración inicial de `usuarios` | `docker compose run --rm api python manage.py makemigrations usuarios` |
| `ModuleNotFoundError` de una librería nueva | La imagen no se reconstruyó | `docker compose build` |
| `port is already allocated` | Otro programa usa el 8000 o el 5432 | Cambia el puerto de la izquierda: `"8001:8000"` |
| El 404 sale en HTML, no en JSON | `DEBUG=True` | Es lo esperado en desarrollo; con `DEBUG=False` responde JSON |
| Un 401 llega como 403 | La primera clase de autenticación no declara `authenticate_header()` | Ver la ficha [T-03](docs/tareas/T-03.md) |

---

## Para estudiar

1. `git log --oneline --reverse` muestra las tareas en el orden en que se construyeron.
2. `git show <commit>` enseña exactamente qué cambió en cada una.
3. Antes de leer el código de una tarea, lee su ficha: [T-01](docs/tareas/T-01.md) · [T-06](docs/tareas/T-06.md) · [T-02](docs/tareas/T-02.md) · [T-03](docs/tareas/T-03.md).

---

Documentación oficial:

- [Django 5.2](https://docs.djangoproject.com/en/5.2/) · [Django REST Framework](https://www.django-rest-framework.org/)
- [Modelo de usuario propio](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
- [Excepciones en DRF](https://www.django-rest-framework.org/api-guide/exceptions/)
- [pytest-django](https://pytest-django.readthedocs.io/) · [factory_boy](https://factoryboy.readthedocs.io/)