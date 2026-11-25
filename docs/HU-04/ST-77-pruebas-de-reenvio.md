# HU-04 — Reenviar el código de activación

## ST-77. Pruebas de reenvío

**Estado:** Completada  
**Responsable:** Daniel Orlando Ceja Olloqui  
**Dependencia:** ST-75, ST-76

### 1. Descripción

Se implementaron pruebas de integración para validar las reglas de negocio y seguridad del endpoint `POST /api/v1/auth/reenviar-codigo/`, así como la restricción de máximo 3 reenvíos por hora por usuario.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/reenvio.py` | Se agregó la validación del límite máximo de 3 reenvíos por hora por usuario respondiendo `429 Too Many Requests` con `Retry-After`. |
| `usuarios/tests/test_reenvio.py` | Se agregaron pruebas para validar la invalidación del código anterior en activación, la respuesta idéntica para cuentas inexistentes/inactivas y el rechazo del cuarto reenvío en una hora. |

### 3. Escenarios probados

- **Código viejo inválido:** Al solicitar un nuevo código y recibirlo, intentar activar la cuenta en `POST /api/v1/auth/activar/` con el código anterior es rechazado (`400 Bad Request`), mientras que el código nuevo activa la cuenta correctamente (`200 OK`).
- **Cuenta inexistente e inactiva responden igual:** El endpoint devuelve exactamente el mismo código HTTP (`200 OK`) y el mismo cuerpo JSON para una cuenta pendiente, una cuenta inexistente y una cuenta inactiva, sin generar códigos para cuentas inactivas.
- **Cuarto reenvío en una hora rechazado:** Tras realizar 3 reenvíos válidos espaciados por más de 60 segundos dentro de una misma ventana de 60 minutos, el cuarto reenvío es rechazado con `429 Too Many Requests` y cabecera `Retry-After`.

### 4. Resultado

Todas las pruebas unitarias y de integración pasan en `pytest` y el código cumple con las reglas de estilo de `ruff`.