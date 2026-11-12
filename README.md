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

Hoy hay **23 pruebas** y todas pasan.

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

### Endpoints

| Método | Ruta | Acceso | Respuesta |
| --- | --- | --- | --- |
| `GET` | `/api/v1/salud/` | Público | `200 {"estado":"ok","bd":"ok"}`, o `503` si PostgreSQL no responde |
| — | `/admin/` | Superusuario | Admin de Django: usuarios, búsqueda por correo y filtros por rol y estado |

### El modelo `Usuario` (T-02)

- Se entra con el **correo**, que es único sin importar mayúsculas: la restricción `email_unico_ci` vive en PostgreSQL.
- El **teléfono** es opcional, único y se guarda en formato E.164 (`+524431234567`).
- La llave primaria es un **UUID**.
- Campos del backlog: `rol` (cliente, operativo, administrador), `estado` (pendiente, activo, inactivo), `canal_preferido` (correo, WhatsApp), `email_verificado`, `telefono_verificado`, `debe_cambiar_password`, `token_version`, `acepto_privacidad_en` y `version_privacidad`.
- Una cuenta nueva es cliente, pendiente y con `token_version = 0`.

> **Regla:** solo `usuario.cambiar_estado(nuevo)` modifica `estado`, `is_active` y `token_version`. Ninguna vista los asigna directamente. Al desactivar, `token_version` sube y se cierran todas las sesiones.

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

`registrar_evento(accion, usuario=None, request=None, resultado="ok", **detalles)` es la única puerta a la bitácora. Hoy escribe una línea JSON en el log `svc.auditoria`; en HU-26 guardará también en una tabla, sin que cambie quien la llama. Las claves sensibles (`password`, `codigo`, `token`...) se guardan como `***`.

```python
from comun.eventos import registrar_evento

registrar_evento("login_fallido", usuario, request, resultado="error", motivo="credenciales")
```

---

## Pruebas y calidad

```bash
docker compose run --rm api pytest              # las 23 pruebas, contra PostgreSQL
docker compose run --rm api pytest usuarios -v  # solo una app, con detalle
docker compose run --rm api ruff check .        # estilo
```

Sin Docker, con un PostgreSQL local y las variables de `.env` exportadas:

```bash
pip install -r requirements-dev.txt
pytest
```

**GitHub Actions** corre en cada push y cada Pull Request: estilo con ruff, revisión de que no falten migraciones (`makemigrations --check`) y pruebas contra PostgreSQL 16. Un Pull Request con el CI en rojo no se fusiona.

Cómo están organizadas las pruebas:

- Cada app tiene su carpeta `tests/`, con un archivo por tema: `test_modelo.py`, `test_errores.py`...
- `usuarios/tests/factories.py` fabrica usuarios válidos: `UsuarioFactory(rol=Rol.ADMINISTRADOR)`. Su contraseña es `PASSWORD_PRUEBA` (`Secreta123`).
- pytest-django corre las pruebas con `DEBUG=False`, como en producción.

---

## Comandos frecuentes

| Para | Comando |
| --- | --- |
| Ver los logs de la API | `docker compose logs -f api` |
| Abrir un shell de Django | `docker compose exec api python manage.py shell` |
| Crear una migración | `docker compose run --rm api python manage.py makemigrations usuarios` |
| Aplicar migraciones | `docker compose exec api python manage.py migrate` |
| Entrar a PostgreSQL | `docker compose exec db psql -U svc -d svc_usuarios` |
| Ver la tabla de usuarios | `docker compose exec db psql -U svc -d svc_usuarios -c "\d usuarios_usuario"` |
| Reconstruir tras cambiar dependencias | `docker compose build` |
| Borrar la base y empezar de cero | `docker compose down -v` |

---

## Cómo trabajamos en equipo

Somos varias personas en un solo repositorio. Estas reglas evitan casi todos los conflictos.

1. **Nadie crea carpetas personales.** El código se acomoda por funcionalidad, no por persona. Quién hizo qué ya lo registran Jira y GitHub.
2. **`main` está protegida.** Todo entra por Pull Request, con el CI en verde y al menos una aprobación.
3. **Una rama por subtarea, con su clave de Jira:** `git switch -c SVC-23-registro`. Que dure uno o dos días.
4. **Sincroniza cada mañana:** `git pull origin main` dentro de tu rama.
5. **Commits pequeños, con la clave al inicio:** `SVC-23: Validar el correo del registro`.
6. **Cada escuadra trabaja en sus archivos**, y cada quien escribe sus pruebas en su propio archivo (`usuarios/tests/test_registro.py`).
7. **`config/`, `usuarios/models.py` y las migraciones** los fusiona el profesor; si necesitas cambiarlos, pide el cambio en tu Pull Request.
8. **Las migraciones no se editan a mano.** Si chocan con las de otra rama, borra la tuya, trae `main` y vuelve a correr `makemigrations`.

**Una subtarea está terminada (Definition of Done)** cuando su Pull Request está fusionado en `main`, el CI está en verde, tiene pruebas y la subtarea está en *Finalizada* en Jira con el enlace al PR.

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

Documentación oficial:

- [Django 5.2](https://docs.djangoproject.com/en/5.2/) · [Django REST Framework](https://www.django-rest-framework.org/)
- [Modelo de usuario propio](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
- [Excepciones en DRF](https://www.django-rest-framework.org/api-guide/exceptions/)
- [pytest-django](https://pytest-django.readthedocs.io/) · [factory_boy](https://factoryboy.readthedocs.io/)

## Documentación de la API (Swagger)
La documentación interactiva de los endpoints está disponible en:
- **Local:** http://localhost:8000/api/docs/
- **Esquema OpenAPI (JSON):** http://localhost:8000/api/schema/