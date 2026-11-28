# T-13 — Definir los roles y las clases de permiso

## ST-122. Crear las clases de permiso en comun/permisos.py

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se crearon las clases de permiso que usan los endpoints del microservicio para autorizar según el rol del usuario. El rol se lee del claim `rol` del token de acceso (`request.auth`) y no de la base de datos. Así otros microservicios pueden reutilizar las mismas clases, y un cambio de rol se refleja en la siguiente renovación del token (HU-14).

### 2. Clases creadas

| Clase | Permite |
|---|---|
| `EsAdministrador` | Solo al rol administrador |
| `EsOperativo` | Solo al rol operativo |
| `EsCliente` | Solo al rol cliente |
| `EsDuenoOAdmin` | Al administrador siempre; a los demás, solo sobre objetos propios (un `Usuario` o un modelo con `usuario_id`) |

También se agregó la función `permisos_por_defecto_mas(*clases)`. DRF reemplaza la lista de permisos cuando un `@action` declara `permission_classes`; esta función suma las clases indicadas a los permisos por defecto para no perder `IsAuthenticated`.

### 3. Respuestas

| Caso | Respuesta |
|---|---|
| Sin token | `401` con código `no_autenticado` |
| Rol equivocado | `403` con código `sin_permiso` |

Los códigos los asigna el manejador de errores de T-03 (`comun/errores.py`).

### 4. Consideraciones

- `EsDuenoOAdmin` solo revisa el objeto si la vista llama a `get_object()`.
- El 401 sin token funciona porque `JWTAuthentication` es la primera clase de `DEFAULT_AUTHENTICATION_CLASSES` (t-04/st-21).
- `ContrasenaDefinitiva`, que también está en `comun/permisos.py`, no es parte de esta subtarea: la agregó la st-116 (HU-12).

### 5. Resultado

Las clases quedaron en `comun/permisos.py` (PR #15), con sus pruebas en ST-125. Desbloquean HU-13 (ST-128 y ST-129) y las usan, entre otras, las vistas de administración de usuarios (st-145, st-149 y st-153).

**ST-122 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).
