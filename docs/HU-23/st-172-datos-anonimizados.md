# HU-23 / ST-172 · Qué datos se anonimizan y cuáles se conservan

**Subtarea:** ID 172 · [Documentación] Definir qué datos se anonimizan y cuáles se conservan
**Historia padre:** HU-23 · Eliminar mi cuenta
**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)
**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-174
**Estado:** En revisión · los puntos marcados con 🤝 se confirman con los otros módulos

## Descripción

Cuando una persona elimina su cuenta (`POST /api/v1/auth/eliminar-cuenta/`, ST-174), el servicio **no borra la fila del usuario**: la **anonimiza**. Así el sistema deja de tener sus datos personales, y los registros que dependen de ella (pedidos en otros módulos, bitácora, historial) siguen siendo consistentes.

Este documento es el **contrato** para la ST-174: dice, campo por campo, qué se anonimiza, qué se borra y qué se conserva, y por qué.

Criterios de HU-23 que cubre:
- *Nombre, correo y teléfono se anonimizan, la cuenta queda inactiva y los registros relacionados se conservan.*
- *Se cierran todas las sesiones.*
- *Llega un correo de confirmación **antes** de anonimizar* (ver §4.1).

## Tres acciones posibles

| Acción | Qué significa | Cuándo se usa |
| --- | --- | --- |
| **Anonimizar** | Se reemplaza el valor por uno que no identifica a nadie. La fila sigue existiendo. | Datos personales en filas que otros registros necesitan |
| **Borrar** | Se elimina la fila completa. | Datos que ya no sirven y que podrían usarse para entrar a la cuenta |
| **Conservar** | Se deja igual. | Datos que no identifican a la persona por sí solos, o que se guardan como evidencia |

---

## 1. Tabla `Usuario` (`usuarios/models.py`)

| Campo | Acción | Valor después de eliminar | Por qué |
| --- | --- | --- | --- |
| `id` (UUID) | **Conservar** | igual | Los otros módulos guardan este id. Si cambia, sus registros quedan huérfanos. |
| `email` | **Anonimizar** | `eliminado-<id>@anonimo.invalid` | Es único y obligatorio, no puede quedar vacío. `.invalid` es un dominio reservado (RFC 2606): nunca le llega correo a nadie. |
| `telefono` | **Anonimizar** | `NULL` | Es único y opcional. Vacío libera el número para otra cuenta. |
| `first_name` | **Anonimizar** | `Usuario` | Texto genérico para que pantallas y reportes muestren "Usuario eliminado". |
| `last_name` | **Anonimizar** | `eliminado` | Ídem. |
| `password` | **Anonimizar** | `set_unusable_password()` | Nadie puede volver a iniciar sesión con esa cuenta. |
| `estado` | **Cambiar** | `inactivo`, con `cambiar_estado()` | Criterio de HU-23. `cambiar_estado()` también pone `is_active=False` y registra el evento. |
| `is_active` | **Cambiar** | `False` | Lo hace `cambiar_estado()`. SimpleJWT rechaza tokens de usuarios inactivos. |
| `token_version` | **Cambiar** | `+1` | Invalida los tokens emitidos antes (criterio: *se cierran todas las sesiones*). |
| `email_verificado` | **Cambiar** | `False` | El correo anonimizado no está verificado. |
| `telefono_verificado` | **Cambiar** | `False` | Ya no hay teléfono. |
| `canal_preferido` | **Cambiar** | `correo` | Ya no hay teléfono para WhatsApp. |
| `debe_cambiar_password` | **Cambiar** | `False` | Ya no aplica. |
| `is_staff`, `is_superuser` | **Cambiar** | `False` | Una cuenta eliminada no debe tener acceso a `/admin/`. |
| `groups`, `user_permissions` | **Borrar** relación | vacíos | Ídem. |
| `rol` | **Conservar** | igual | No identifica a la persona y sirve para estadísticas. Además, la regla *"el único administrador no puede eliminarse"* se valida **antes** de anonimizar. |
| `date_joined` | **Conservar** | igual | No identifica por sí solo; sirve para métricas. |
| `last_login` | **Conservar** | igual | Ídem. |
| `acepto_privacidad_en` | **Conservar** | igual | **Evidencia** de que la persona aceptó el aviso de privacidad mientras usó el servicio. |
| `version_privacidad` | **Conservar** | igual | Ídem. |

### Campo nuevo recomendado: `eliminado_en` 🤝

Hoy `estado = inactivo` significa dos cosas: *"el administrador la desactivó"* (HU-17) y *"la persona la eliminó"* (HU-23). La diferencia importa: una cuenta desactivada se puede reactivar, pero una eliminada no.

**Propuesta para ST-174:** agregar `eliminado_en = models.DateTimeField(null=True, blank=True)` a `Usuario`.
- `eliminado_en` con valor → la cuenta se eliminó. Ningún endpoint puede reactivarla.
- Toca `usuarios/models.py` y requiere una migración, así que lo fusiona el profesor (regla 7 del README).

---

## 2. Tablas relacionadas

| Tabla | Datos personales que guarda | Acción | Por qué |
| --- | --- | --- | --- |
| `CodigoVerificacion` (`usuarios`) | hash del código, canal | **Borrar** todos los del usuario | Ya no sirven, y un código vigente podría reactivar o recuperar la cuenta. |
| `Dispositivo2FA` (`usuarios`) | secreto TOTP cifrado | **Borrar** | Es una credencial; no tiene uso después de eliminar. |
| `RegistroAcceso` (`usuarios`, HU-22) | IP, user agent, dispositivo, fecha | **Conservar** | *"Los registros relacionados se conservan."* Ya no apuntan a una persona identificable, y la limpieza de 90 días (ST-169) los borra con el tiempo. |
| `EventoAuditoria` (`comun`, HU-26) | IP, user agent, `detalles` | **Conservar** | Es la bitácora de seguridad: debe mostrar que la cuenta existió y que se eliminó. `detalles` ya pasa por `limpiar_detalles()` y no guarda contraseñas, códigos ni tokens. |
| `Notificacion` (`notificaciones`), ya enviadas o fallidas | `contexto` (puede llevar nombre o código) | **Conservar** la fila, **vaciar** `contexto` (`{}`) | Se conserva el historial de envíos sin los datos del mensaje. |
| `Notificacion`, pendientes | `contexto` | **Borrar**, **excepto** la confirmación de eliminación (§4.1) | No tiene sentido enviar avisos a una cuenta eliminada. |
| `OutstandingToken` / `BlacklistedToken` (SimpleJWT `token_blacklist`) | `jti`, fechas, usuario | **Conservar** y **poner en lista negra** todos los refresh tokens del usuario | Complementa `token_version += 1`: ningún refresh token puede renovar sesión. |
| `AccessAttempt` / `AccessLog` (django-axes, HU-25) | `username` = **el correo escrito** al iniciar sesión, IP | **Borrar** los del correo original, con `axes.utils.reset(username=<correo original>)` **antes** de anonimizar | Es la única tabla que guarda el correo **en texto**, sin relación con el usuario. Si no se borra, el correo sobrevive a la eliminación. |

### Bitácora en archivos o consola (`svc.auditoria`)

Los eventos registran `usuario_id`, nunca el correo, así que no hace falta tocarlos.

---

## 3. Orden recomendado para ST-174

Todo dentro de `transaction.atomic()`, salvo el envío real del correo:

1. Validar la contraseña y la palabra `ELIMINAR`.
2. Validar que **no sea el único administrador** (si `rol == administrador` y no hay otro administrador activo → error).
3. Guardar en una variable el **correo original** (para axes y para el correo de confirmación).
4. Encolar el **correo de confirmación** (§4.1).
5. Borrar `CodigoVerificacion`, `Dispositivo2FA` y las notificaciones pendientes (salvo la de confirmación); vaciar `contexto` de las demás.
6. `axes.utils.reset(username=correo_original)`.
7. Poner en lista negra los refresh tokens del usuario.
8. Anonimizar `Usuario` (§1), `token_version += 1`, `cambiar_estado(inactivo)` y `eliminado_en = now()`.
9. `registrar_evento("cuenta_eliminada", usuario, request)`, sin el correo en `detalles`.

---

## 4. Puntos para acordar 🤝

### 4.1 El correo de confirmación no debe llegar a la dirección anonimizada (equipo de notificaciones, T-07/T-10)

HU-23 pide que llegue un correo de confirmación **antes** de anonimizar. Pero el worker obtiene la dirección **al momento de enviar**:

```python
# notificaciones/worker.py
def destino_de(notificacion):
    ...
    return usuario.email
```

Si la cuenta se anonimiza en la misma petición, cuando el worker toma la notificación (unos segundos después), `usuario.email` ya es `eliminado-…@anonimo.invalid` y **el correo nunca llega**.

| Opción | Cómo | Ventaja | Desventaja |
| --- | --- | --- | --- |
| **A (recomendada)** | Agregar a `Notificacion` un campo `destino` que se llena al encolar; el worker lo usa si existe | Sirve para cualquier aviso futuro; el correo llega aunque el usuario cambie | Toca el modelo de `notificaciones` y requiere una migración |
| B | Enviar el correo de confirmación **directo** (sin la bandeja), antes de anonimizar | No cambia modelos | Si falla el envío, la petición tarda o falla; rompe el patrón de la bandeja de salida |
| C | Anonimizar **después** de que el worker envíe el correo | Sin cambios de modelo | La cuenta queda un tiempo sin anonimizar; más complejo de coordinar |

### 4.2 Otros microservicios (pedidos, catálogo, …)

| Pregunta | Propuesta |
| --- | --- |
| ¿Qué hacen con el `id` de un usuario eliminado? | Lo conservan. Sus registros siguen siendo válidos. |
| ¿Qué muestran como nombre? | Lo que les dé svc-usuarios: `Usuario eliminado`. No deben copiar ni guardar el correo o el teléfono. |
| ¿Cómo se enteran? | Por el token: con `is_active=False` y `token_version` nuevo, cualquier token del usuario deja de servir. Si guardan datos personales propios (por ejemplo, una dirección de envío), se acuerda un aviso (evento o endpoint) para que los anonimicen también. |

### 4.3 Decisiones internas

| Pregunta | Propuesta |
| --- | --- |
| ¿Conservar IP y user agent en `RegistroAcceso` y `EventoAuditoria`? | Sí. Son registros de seguridad, y `RegistroAcceso` se borra solo a los 90 días. |
| ¿Se puede recuperar una cuenta eliminada? | No. La anonimización es irreversible. La persona puede registrarse de nuevo con el mismo correo, que queda libre. |
| ¿Se agrega `eliminado_en`? | Sí (§1). |

---

## 5. Resumen

| Dato | Acción |
| --- | --- |
| Nombre, apellidos, correo, teléfono | Anonimizar |
| Contraseña | Inutilizable |
| Estado | `inactivo`, y se cierran todas las sesiones |
| id, rol, fechas, aceptación de privacidad | Conservar |
| Códigos de verificación, 2FA, notificaciones pendientes | Borrar |
| Historial de accesos, bitácora, notificaciones enviadas | Conservar (sin el contenido del mensaje) |
| Intentos de login de django-axes | Borrar (guardan el correo en texto) |