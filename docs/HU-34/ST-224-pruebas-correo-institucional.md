# HU-34 — Generar el correo institucional al dar de alta

## ST-224. Pruebas de generar_correo_institucional()

**Estado:** Completada (esperando revisión)
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción

Se escribieron las pruebas unitarias para la función `generar_correo_institucional()` (desarrollada por Juan Diego en la ST-223). Las pruebas aseguran que la función limpia acentos, maneja la letra "ñ" correctamente y evita generar correos duplicados si ya existen en la base de datos.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_utils.py` | Creación de 3 pruebas unitarias para la función. |
| `docs/HU-34/ST-224-pruebas-correo-institucional.md` | Documentación de la subtarea. |

### 3. Resultado

Las 3 pruebas pasan en verde. La función es robusta y cumple con los criterios de aceptación de la historia.

**ST-224 finalizada.**