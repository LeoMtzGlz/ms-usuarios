# T-06 — Configurar pruebas automáticas e integración continua

## ST-29. Crear el workflow de GitHub Actions

**Estado:** Completada  
**Responsable:** l22420415

### 1. Descripción

Se creó el workflow de integración continua `.github/workflows/ci.yml`. En cada push a cualquier rama y en cada Pull Request hacia `development` o `main`, GitHub levanta un PostgreSQL 16, instala las dependencias y revisa estilo, migraciones y pruebas. Si algo falla, el check queda en rojo y el PR no debe fusionarse.

También se corrigió el único error de ruff que había en el repositorio (E501, línea de más de 120 caracteres en un comentario de `config/settings.py`), para que el CI arranque en verde.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `.github/workflows/ci.yml` | Workflow `CI` con el job `pruebas` |
| `config/settings.py` | Solo se acortó el comentario de la línea 90 (E501) |

### 3. Qué hace el workflow

**Cuándo corre:** en cada `push` a cualquier rama y en cada `pull_request` hacia `development` o `main`. Si llega un push nuevo a la misma rama mientras otra ejecución sigue en curso, la anterior se cancela (`concurrency` con `cancel-in-progress`).

**Dónde corre:** `ubuntu-latest`, con un servicio `postgres:16` en `localhost:5432`. El job espera a que la base responda (`pg_isready`) antes de empezar.

**Variables de entorno** (solo para CI, no son secretos reales):

| Variable | Valor | Motivo |
|---|---|---|
| `SECRET_KEY` | clave de prueba | Obligatoria: sin ella Django no arranca |
| `DATABASE_URL` | `postgres://ms_user:ms_password@localhost:5432/ms_usuarios` | Obligatoria: `env.db()` no tiene valor por defecto |
| `DEBUG` | `False` | Igual que en producción |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts aceptados |

**Pasos:**

| Paso | Comando | Qué revisa |
|---|---|---|
| Descargar el código | `actions/checkout@v7` | Trae el commit que se va a probar |
| Instalar Python 3.12 | `actions/setup-python@v7` | Misma versión que el `Dockerfile`; guarda en caché los paquetes de pip según `requirements.txt` |
| Instalar dependencias | `pip install -r requirements.txt` | Que las versiones fijadas se instalen sin conflictos |
| Revisar estilo | `ruff check .` | Reglas de `pyproject.toml` (E y F, líneas de hasta 120) |
| Revisar migraciones | `python manage.py makemigrations --check --dry-run` | Que ningún cambio en los modelos se quede sin su migración |
| Aplicar migraciones | `python manage.py migrate --noinput` | Que las migraciones se apliquen limpias sobre PostgreSQL 16 |
| Correr pruebas | `pytest` | Todas las pruebas de `comun`, `usuarios` y `notificaciones` |

### 4. Nombre del check

El job se llama **`pruebas`** (id y nombre). Es el check que en ST-30 se marcará como obligatorio para proteger la rama, así que **no debe renombrarse**: si cambia, la protección de rama dejaría de reconocerlo.

### 5. Cómo ver los resultados

1. En GitHub, abrir la pestaña **Actions** del repositorio.
2. Elegir el workflow **CI** y la ejecución del commit o PR.
3. Entrar al job **pruebas** y abrir el paso que falló para ver su salida.

En un Pull Request, el resultado aparece al final de la conversación como **CI / pruebas** con una palomita verde o una cruz roja; **Details** lleva directo al registro.

### 6. Qué hacer si el CI falla

Cada paso se puede reproducir en local con Docker antes de volver a subir:

| Paso que falla | Cómo reproducirlo | Solución habitual |
|---|---|---|
| Revisar estilo | `docker compose run --rm api ruff check .` | Corregir lo que indica; muchas cosas se arreglan con `ruff check --fix .` |
| Revisar migraciones | `docker compose run --rm api python manage.py makemigrations --check --dry-run` | Generar la migración que falta con `makemigrations <app>` y subirla en el mismo PR |
| Aplicar migraciones | `docker compose run --rm api python manage.py migrate` | Suele ser un choque de migraciones con otra rama: traer `development`, borrar la migración propia y volver a correr `makemigrations` (no editarlas a mano) |
| Correr pruebas | `docker compose run --rm api pytest -v` | Leer la prueba que falla y corregir el código o la prueba |
| Instalar dependencias | `docker compose build` | Revisar la versión agregada en `requirements.txt` |

### 7. Resultado

El repositorio cuenta con integración continua: cada push y cada PR se revisan automáticamente contra PostgreSQL 16, y el check `pruebas` queda disponible para exigirlo en la protección de ramas (ST-30).

**ST-29 finalizada.**

**Responsable de la actividad:** l22420415.
