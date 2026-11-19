# ST-193 – Configurar el logger de seguridad

**Estado:** Implementada, pendiente de revisión
**Responsable:** Daniel Gómez Villaseñor (gomez-d)
**Subtarea:** ST-193

## Descripción

Se configuró el logger de seguridad para registrar eventos tanto en consola como en un archivo. También se incorporaron filtros para ocultar datos sensibles en los mensajes de registro, incluyendo contraseñas, códigos y tokens.

## Implementación

- Se creó `comun/filtros_logging.py` con el filtro `FiltrosDatosSensibles`.
- Se configuraron los handlers de consola y archivo en `config/settings.py`.
- Se estableció el archivo de salida `logs/seguridad.log`.
- Se aplicó un filtro normal a la consola y un filtro estricto al archivo.
- El filtro estricto trabaja sobre una copia del registro y oculta también JWT y cualquier número de seis dígitos.
- Se incorporó el ocultamiento de datos sensibles en los tracebacks.
- Se agregó `logs/` a `.gitignore` para evitar subir los registros al repositorio.
- Se añadieron pruebas en `comun/tests/test_logging.py`.

## Resultado

El logger escribe los registros en consola y archivo. La consola utiliza el filtro normal, mientras que el archivo aplica el filtro estricto para evitar que códigos de activación, JWT y otros datos sensibles contemplados por la implementación queden registrados en claro.

## Validaciones

- `ruff check .`: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `pytest`: 144 pruebas aprobadas.
- `comun/tests/test_logging.py`: 12 pruebas aprobadas.
- `git diff --check`: sin errores.
