# HU-04 — Reenviar el código de activación

## ST-76. Aplicar la espera de 60 segundos

**Estado:** Completada  
**Responsable:** Alondra Alejandra López Medellín  
**Revisor:** Daniel Ceja  
**Dependencia:** ST-75

### 1. Descripción

Se implementó una restricción de tiempo en el endpoint `POST /api/v1/auth/reenviar-codigo/`, estableciendo una espera mínima de 60 segundos entre solicitudes de reenvío del código de activación.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/reenvio.py` | Se agregó la validación del tiempo transcurrido desde la creación del último código de activación. |
| `usuarios/tests/test_reenvio.py` | Se agregaron pruebas para validar el bloqueo y la autorización del reenvío según el tiempo transcurrido. |

### 3. Comportamiento

- Si no han transcurrido 60 segundos desde la generación del último código de activación, el endpoint responde con `429 Too Many Requests`.
- La respuesta incluye la cabecera `Retry-After`, indicando los segundos restantes para poder solicitar otro código.
- Si han transcurrido 60 segundos o más, se permite generar un nuevo código.
- El código anterior se invalida cuando se genera uno nuevo.
- La validación considera el último código de activación generado, independientemente de si fue creado durante el registro inicial o mediante un reenvío anterior.
- Se mantiene la respuesta genérica para usuarios inexistentes y cuentas que no están pendientes de activación.
- Se utiliza un bloqueo de registro del usuario para evitar solicitudes simultáneas de reenvío.

### 4. Pruebas

Se verifican los siguientes escenarios:

- Reenvío permitido después de 60 segundos.
- Reenvío bloqueado antes de cumplir los 60 segundos.
- Respuesta HTTP `429 Too Many Requests` cuando se solicita un reenvío antes del tiempo permitido.
- Inclusión de la cabecera `Retry-After` con los segundos restantes.
- Invalidación del código anterior cuando se genera uno nuevo.
- Respuesta genérica para usuarios inexistentes.
- Restricción para cuentas que no están pendientes de activación.
- Bloqueo del primer reenvío cuando todavía no han transcurrido 60 segundos desde la generación del código durante el registro inicial.

### 5. Resultado

La implementación establece un intervalo mínimo de 60 segundos entre generaciones de códigos de activación y conserva el comportamiento de seguridad implementado en ST-75.

