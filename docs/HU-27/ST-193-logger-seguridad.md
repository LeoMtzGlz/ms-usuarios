# ST-193 – Configurar el logger de seguridad

**Estado:** Implementada, pendiente revisión
**Responsable:** Daniel Gómez Villaseñor (gomez-d)
**Subtarea:** ST-193

## Descripción

Se configuró el logger de seguridad para registrar eventos tanto en consola como en un archivo. También se incorporó un filtro para ocultar datos sensibles en los mensajes de registro, incluyendo contraseñas, códigos y tokens.

## Implementación

- Se creó `comun/filtros_logging.py` con el filtro `FiltrosDatosSensibles`.
- Se configuraron los handlers de consola y archivo en `config/settings.py`.
- Se estableció el archivo de salida `logs/seguridad.log`.
- Se aplicó el filtro de datos sensibles a ambos handlers.
- Se agregó `logs/` a `.gitignore` para evitar subir los registros al repositorio.
- Se añadieron pruebas en `comun/tests/test_logging.py`.

## Resultado

El logger escribe los registros en consola y archivo, aplicando el filtro para enmascarar los datos sensibles contemplados por su implementación.

## Validaciones

- `ruff check .`: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios detectados.
- `pytest`: 142 pruebas aprobadas.
- `git diff --check`: sin errores.
