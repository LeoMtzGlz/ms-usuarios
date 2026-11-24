# T-35 — Gestión de contraseñas

## ST-113. Emitir tokens nuevos para el dispositivo actual

**Estado:** Completada  
**Responsable:** Alondra Alejandra López Medellin  
**Revisa:** Isamar Chávez

### 1. Descripción

Se implementó la emisión de nuevos tokens JWT después de que un usuario autenticado cambia correctamente su contraseña, permitiendo que continúe utilizando su sesión en el dispositivo actual sin necesidad de iniciar sesión nuevamente.

### 2. Implementación

Para integrar esta funcionalidad se realizaron las siguientes acciones:

- Se integró la generación de tokens en `CambiarPasswordView`, después de completar correctamente el cambio de contraseña.
- Se utiliza `CustomTokenObtainPairSerializer.get_token(usuario)` para generar un nuevo token refresh.
- Se conservan los claims personalizados definidos en el proyecto.
- A partir del nuevo refresh se genera el token access correspondiente.

### 3. Respuesta exitosa

Cuando el cambio de contraseña se realiza correctamente, el endpoint devuelve una respuesta HTTP `200 OK` con el siguiente formato:

```json
{
    "mensaje": "Contraseña actualizada correctamente.",
    "access": "<nuevo_access>",
    "refresh": "<nuevo_refresh>"
}
```

### 4. Claims incluidos

Los nuevos tokens conservan los siguientes claims personalizados:

- `user_id`
- `rol`
- `email_verificado`
- `token_version`
- `debe_cambiar_password`
- `zona_id`

### 5. Consideraciones

- Los tokens se generan después de actualizar correctamente la contraseña.
- Se utiliza el serializer personalizado de JWT para conservar los claims del proyecto.
- Se mantiene la configuración de firma RS256.
- El usuario puede continuar utilizando el dispositivo actual con los nuevos tokens.
- Al cambiar la contraseña, se incrementa el valor de `token_version` del usuario.
- Actualmente, el sistema no compara el `token_version` incluido en el token con el almacenado en la base de datos para rechazar tokens anteriores. Por lo tanto, la invalidación de sesiones anteriores queda pendiente de implementar en una subtarea posterior.

### 6. Dependencias

- ST-112: Endpoint para cambiar contraseña.
- ST-117: Método `Usuario.cambiar_password()`.
- ST-83: Claims personalizados de JWT.

**ST-113 finalizada.**

**Responsable de la actividad:** Alondra Alejandra López Medellin.