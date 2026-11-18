# T-06 — Configurar pruebas automáticas e integración continua

## ST-31. Documentar cómo ejecutar las pruebas

**Estado:** En desarrollo  
**Responsable:** l22420423@jiquilpan.tecnm.mx

### 1. Descripción

Se documentan los procedimientos necesarios para ejecutar las pruebas automatizadas del microservicio `ms-usuarios`, tanto desde un entorno local de Python como mediante Docker Compose.

También se incluyen las comprobaciones de estilo, la verificación de migraciones y la solución de errores frecuentes.

### 2. Requisitos previos

Para ejecutar las pruebas localmente se requiere:

- Python y un entorno virtual con las dependencias instaladas.
- PostgreSQL disponible y configurado.
- Archivo `.env` con las variables de entorno necesarias.
- Configuración de pytest mediante `pytest.ini`.

Para ejecutarlas mediante Docker se requiere:

- Docker Desktop o Docker Engine.
- Docker Compose.
- Los servicios definidos en `docker-compose.yml`.
- Una conexión válida entre el contenedor de la API y PostgreSQL.

**Nota:** La configuración del proyecto utiliza PostgreSQL 16.

### 3. Ejecución local de las pruebas

#### 3.1. Preparar el entorno virtual

Desde la raíz del repositorio, activar el entorno virtual en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar o actualizar las dependencias:

```powershell
python -m pip install -r requirements.txt
```

#### 3.2. Configurar PostgreSQL

Cuando Django se ejecuta directamente desde Windows y PostgreSQL utiliza el puerto publicado por Docker, la variable `DATABASE_URL` debe apuntar a `localhost:5433`.

Ejemplo:

```env
DATABASE_URL=postgres://ms_user:ms_password@localhost:5433/ms_usuarios
```

Los valores deben corresponder a la configuración real del entorno.

Iniciar PostgreSQL, si todavía no está ejecutándose:

```powershell
docker compose up -d db
```

Verificar el estado:

```powershell
docker compose ps
```

El servicio debe aparecer como `healthy`.

#### 3.3. Ejecutar las pruebas

Ejecutar todas las pruebas:

```powershell
python -m pytest
```

Ejecutar las pruebas mostrando el resultado individual:

```powershell
python -m pytest -v
```

Ejecutar las pruebas de una aplicación:

```powershell
python -m pytest usuarios -v
```

Ejecutar un archivo específico:

```powershell
python -m pytest usuarios/tests/test_modelo.py -v
```

pytest utiliza `pytest.ini` para cargar `config.settings` y descubrir las pruebas de `comun`, `usuarios` y `notificaciones`.

### 4. Ejecución de pruebas con Docker

#### 4.1. Preparar los servicios

Construir la imagen de la API:

```powershell
docker compose build
```

Iniciar PostgreSQL:

```powershell
docker compose up -d db
```

Comprobar que se encuentra disponible:

```powershell
docker compose ps
```

#### 4.2. Configuración de la conexión

Dentro de Docker, PostgreSQL utiliza el nombre del servicio `db` y el puerto interno `5432`.

Por lo tanto, la conexión correspondiente es:

```env
DATABASE_URL=postgres://ms_user:ms_password@db:5432/ms_usuarios
```

Cuando el archivo `.env` local utiliza `localhost:5433`, es posible sobrescribir `DATABASE_URL` solamente durante la ejecución del contenedor, sin modificar el archivo.

#### 4.3. Ejecutar las pruebas

Ejecutar todas las pruebas:

```powershell
docker compose run --rm -e DATABASE_URL=postgres://ms_user:ms_password@db:5432/ms_usuarios api python -m pytest
```

Ejecutarlas en modo detallado:

```powershell
docker compose run --rm -e DATABASE_URL=postgres://ms_user:ms_password@db:5432/ms_usuarios api python -m pytest -v
```

Este procedimiento ejecuta pytest dentro de un contenedor temporal de la API y utiliza PostgreSQL mediante la red interna de Docker Compose.

### 5. Comprobaciones adicionales de calidad

#### 5.1. Verificación de estilo

Desde el entorno local:

```powershell
python -m ruff check .
```

Resultado esperado:

```text
All checks passed!
```

#### 5.2. Verificación de migraciones

Ejecutar:

```powershell
python manage.py makemigrations --check --dry-run
```

Resultado esperado cuando no existen cambios pendientes:

```text
No changes detected
```

Estas comprobaciones también forman parte del workflow de integración continua.

### 6. Integración continua con GitHub Actions

El workflow `.github/workflows/ci.yml` ejecuta automáticamente las comprobaciones del proyecto.

Se activa durante los eventos de `push` y en los Pull Requests dirigidos a `development` y `main`.

El job `pruebas` realiza las siguientes operaciones:

1. Descarga el código del repositorio.
2. Configura Python 3.12.
3. Instala las dependencias del proyecto.
4. Verifica el estilo mediante Ruff.
5. Comprueba que no falten migraciones.
6. Aplica las migraciones en PostgreSQL 16.
7. Ejecuta las pruebas mediante pytest.

El resultado puede consultarse desde la pestaña **Actions** de GitHub o desde la sección de comprobaciones del Pull Request.

El check `pruebas` forma parte de la protección de las ramas principales.

### 7. Solución de problemas frecuentes

#### 7.1. ModuleNotFoundError

Ejemplo:

```text
ModuleNotFoundError: No module named 'rest_framework_simplejwt'
```

**Causa:** falta una dependencia en el entorno virtual.

**Solución:**

```powershell
python -m pip install -r requirements.txt
```

#### 7.2. Error de conexión a PostgreSQL

Ejemplo:

```text
django.db.utils.OperationalError: connection timeout expired
```

**Posibles causas:**

- PostgreSQL no está iniciado.
- El contenedor todavía no está disponible.
- La conexión utiliza un host o puerto incorrecto.

**Solución:**

Comprobar el estado del servicio:

```powershell
docker compose ps
```

Iniciar PostgreSQL cuando sea necesario:

```powershell
docker compose up -d db
```

Verificar que `DATABASE_URL` corresponda al entorno utilizado:

| Entorno | Host | Puerto |
|---|---|---|
| Windows | `localhost` | `5433` |
| Docker | `db` | `5432` |

#### 7.3. Errores de Ruff

Si el comando `ruff check .` devuelve errores, revisar los archivos y las líneas indicadas.

Las correcciones deben respetar las convenciones establecidas en el proyecto.

#### 7.4. Migraciones pendientes

Si `makemigrations --check --dry-run` detecta modificaciones, revisar los cambios en los modelos y comprobar si falta generar una migración.

No modificar ni eliminar migraciones existentes sin revisar previamente las dependencias con el equipo.

### 8. Resultados de las pruebas

Durante la verificación de la ST-31 se obtuvieron los siguientes resultados:

| Comprobación | Resultado |
|---|---|
| Ejecución local con pytest | 137 pruebas correctas |
| Ejecución mediante Docker | 137 pruebas correctas |
| Ruff | Sin errores |
| Verificación de migraciones | Sin cambios pendientes |

La ejecución local se realizó desde Windows utilizando un entorno virtual de Python. La ejecución con Docker utilizó PostgreSQL mediante el servicio `db`.

Las pruebas se realizaron con la versión del proyecto disponible durante el desarrollo de esta subtarea. La cantidad de pruebas puede cambiar conforme se integren nuevas funcionalidades.

### 9. Resultado

Se verificaron y documentaron los procedimientos para ejecutar las pruebas automatizadas del microservicio en los entornos local y Docker.

También se documentaron las comprobaciones adicionales utilizadas en GitHub Actions y los errores de configuración identificados durante la ejecución.

**Responsable de la actividad:** l22420423@jiquilpan.tecnm.mx.