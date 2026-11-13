# T-06 — Configurar pruebas automáticas e integración continua

## ST-28. Instalar pytest-django y factory-boy

**Estado:** Completada  
**Responsable:** l22420415

### 1. Descripción

Se dejó lista la base de pruebas automáticas del microservicio: pytest con pytest-django para correr las pruebas contra la base de datos de Django, factory-boy para fabricar datos de prueba y ruff para revisar el estilo. Las tres librerías ya estaban en `requirements.txt`, pero sin versión; ahora tienen versión exacta para que todo el equipo, Docker y el CI instalen lo mismo.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `requirements.txt` | Versiones fijas: `pytest-django==4.14.0`, `factory-boy==3.3.3`, `ruff==0.17.5` |
| `pytest.ini` | `notificaciones` se agregó a `testpaths`, para que sus pruebas también se ejecuten |
| `conftest.py` (raíz) | Fixtures compartidos `api_client` y `usuario` |
| `usuarios/tests/test_fixtures.py` | Prueba mínima que demuestra que los fixtures funcionan |

### 3. Versiones y compatibilidad

| Librería | Versión | Compatibilidad |
|---|---|---|
| pytest-django | 4.14.0 | Declara soporte para Django 5.2 y Python 3.12; requiere `pytest>=7` (usamos 9.2.0) |
| factory-boy | 3.3.3 | Python 3.12; su metadata llega hasta Django 5.1, pero usa la API estable del ORM y funciona con Django 5.2 (lo confirman las pruebas) |
| ruff | 0.17.5 | Herramienta independiente; se configura en `pyproject.toml` (`target-version = "py312"`) |

### 4. Fixtures disponibles

Se definen en `conftest.py` y cualquier prueba los recibe como parámetro, sin importarlos:

```python
def test_algo(api_client, usuario):
    api_client.force_authenticate(usuario)
    ...
```

- `api_client`: `rest_framework.test.APIClient` sin sesión iniciada.
- `usuario`: usuario activo creado con `UsuarioFactory`; su contraseña es `PASSWORD_PRUEBA` (`Secreta123`). Activa el acceso a la base por sí solo.

### 5. Cómo correr las pruebas

Con Docker (requiere un `.env` cuyo `DATABASE_URL` coincida con `docker-compose.yml`, por ejemplo `postgres://ms_user:ms_password@db:5432/ms_usuarios`):

```bash
docker compose build                        # tras cambiar requirements.txt
docker compose run --rm api pytest          # todas las pruebas, contra PostgreSQL 16
docker compose run --rm api pytest usuarios -v
docker compose run --rm api ruff check .
```

### 6. ¿Por qué no se creó `requirements-dev.txt`?

- El `Dockerfile` instala solo `requirements.txt`; con un segundo archivo, la imagen no tendría pytest ni ruff y `docker compose run --rm api pytest` dejaría de funcionar.
- El CI (ST-29) necesita las mismas dependencias que Docker; un solo archivo evita que se desincronicen.
- En el alcance de esta subtarea no se toca el `Dockerfile`. Separar dependencias de desarrollo y producción queda como mejora futura, cuando exista una imagen de producción.

### 7. Resultado

Las dependencias de pruebas quedaron con versión fija, las tres apps están incluidas en la ejecución de pytest y existen fixtures compartidos para las siguientes historias.

**ST-28 finalizada.**

**Responsable de la actividad:** l22420415.
