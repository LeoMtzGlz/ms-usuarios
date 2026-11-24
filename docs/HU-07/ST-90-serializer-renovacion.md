# HU-07 — Renovar mi sesión sin volver a iniciar sesión

## ST-90. Crear el serializer de renovación propio

**Estado:** En desarrollo  
**Responsable:** Claudia Maritza Santibáñez García (l22420423)

### 1. Descripción

Se implementó un serializer personalizado de Django REST Framework y SimpleJWT para renovar tokens JWT, verificando la información actual del usuario antes de emitir nuevos tokens.

La implementación permite renovar una sesión sin volver a proporcionar las credenciales de inicio de sesión, siempre que el refresh token sea válido y la cuenta continúe habilitada.

### 2. Archivos modificados

| Archivo | Cambio |
|---|---|
| `usuarios/tokens.py` | Implementación de `CustomTokenRefreshSerializer` |
| `usuarios/views.py` | Creación de `CustomTokenRefreshView` |
| `usuarios/urls.py` | Registro del endpoint de renovación |
| `usuarios/tests/test_refresh_st90.py` | Pruebas de funcionalidad y seguridad |

### 3. Endpoint de renovación

**Método:** `POST`

**Ruta:** `/api/v1/auth/token/renovar/`

Ejemplo de solicitud:

```json
{
    "refresh": "<refresh_token>"
}
```

Respuesta exitosa:

```json
{
    "access": "<nuevo_access_token>",
    "refresh": "<nuevo_refresh_token>"
}
```

### 4. Validaciones de seguridad

El serializer realiza las siguientes verificaciones:

1. Valida el refresh token recibido mediante SimpleJWT.
2. Obtiene y valida el identificador UUID del usuario.
3. Consulta el usuario actual en PostgreSQL.
4. Comprueba que la cuenta tenga estado `activo`.
5. Verifica que `is_active` sea verdadero.
6. Compara el claim `token_version` con el valor vigente en la base de datos.
7. Rechaza los tokens asociados con usuarios inexistentes o sesiones invalidadas.

Las renovaciones rechazadas utilizan el sistema de errores del proyecto, incluyendo `TokenInvalido` cuando corresponde.

### 5. Actualización de claims

Antes de generar el nuevo access token, se actualizan los siguientes claims con los datos vigentes del usuario:

| Claim | Descripción |
|---|---|
| `rol` | Rol actual del usuario |
| `email_verificado` | Estado actual de verificación del correo |
| `token_version` | Versión vigente de la sesión |
| `debe_cambiar_password` | Indicador de contraseña temporal |
| `zona_id` | Identificador de la zona asignada |

Esto permite reflejar cambios realizados después del inicio de sesión.

### 6. Rotación y lista negra

La renovación utiliza la funcionalidad de blacklist de SimpleJWT:

- El refresh anterior se agrega a `BlacklistedToken`.
- Se genera un nuevo identificador `jti`.
- Se actualiza la fecha de emisión y expiración.
- El nuevo refresh se registra en `OutstandingToken`.
- El refresh anterior no puede reutilizarse en renovaciones secuenciales.

### 7. Compatibilidad con `recordarme`

Se conserva la duración configurada durante el inicio de sesión:

| Valor de `recordarme` | Duración del refresh |
|---|---|
| `false` | 1 día |
| `true` | 7 días |

La duración del access token permanece en 15 minutos, conforme a la configuración existente de SimpleJWT.

### 8. Protección transaccional

Se incorporaron `transaction.atomic()` y `select_for_update()` para serializar las renovaciones que afectan a un mismo usuario.

Después de adquirir el bloqueo, se vuelve a comprobar la lista negra del refresh recibido.

Esta implementación busca impedir que dos solicitudes simultáneas reutilicen el mismo refresh token.

Se ejecutó una prueba concurrente mediante conexiones independientes a PostgreSQL. En la ejecución realizada, una solicitud renovó correctamente y la otra fue rechazada.

Esta prueba no constituye una garantía exhaustiva frente a todas las posibles condiciones de carrera.

### 9. Pruebas realizadas

Se implementaron y ejecutaron 11 pruebas específicas en `usuarios/tests/test_refresh_st90.py`.

Se verificaron:

- Renovación correcta y rotación de tokens.
- Rechazo de tokens con `token_version` anterior.
- Rechazo de usuarios inactivos.
- Actualización de claims.
- Conservación de siete días con `recordarme=True`.
- Rechazo de refresh tokens malformados.
- Rechazo de usuarios inexistentes.
- Rechazo de UUID inválidos.
- Rechazo de usuarios pendientes.
- Persistencia de la lista negra y los tokens registrados.
- Renovación concurrente utilizando el mismo refresh.

**Resultado:** 11 pruebas aprobadas.

#### Verificación general del proyecto

Se ejecutó:

```powershell
python -m pytest -q
```

Resultado:

```text
557 passed, 2 xfailed in 108.40s
```

También se realizaron verificaciones de Django, Ruff y migraciones.

### 10. Dependencias

- **ST-85:** duración del refresh según `recordarme`.
- **ST-89:** rotación y lista negra de SimpleJWT.
- **ST-91:** limpieza periódica de tokens vencidos.
- **ST-92:** pruebas formales y ampliación de escenarios de renovación.

### 11. Resultado

Se implementó el serializer de renovación propio y se integró con el endpoint de HU-07.

Las pruebas funcionales verificaron la renovación, la rotación, la invalidación de sesiones, la actualización de claims y la conservación de `recordarme`.

**Pendiente:** revisión final del código y de las condiciones de integración antes de enviar el Pull Request.