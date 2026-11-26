# HU-11 — Gestión de contraseñas

## ST-112. Crear endpoint para cambiar contraseña

**Estado:** Completada  
**Responsable:** Alondra Alejandra López Medellin

### 1. Descripción

Se implementó un endpoint que permite a un usuario autenticado cambiar su contraseña actual por una nueva, verificando que los datos proporcionados cumplan con las validaciones de seguridad establecidas en el proyecto.

### 2. Datos del endpoint

| Campo | Información |
|---|---|
| Método HTTP | POST |
| Ruta | `/api/v1/auth/cambiar-password/` |
| Permiso | `IsAuthenticated` |
| Código de respuesta exitosa | 200 OK |

### 3. Datos de entrada

El endpoint recibe los siguientes campos:

| Campo | Descripción |
|---|---|
| `password_actual` | Contraseña actual del usuario. |
| `password_nueva` | Nueva contraseña que desea establecer. |
| `password_confirmacion` | Confirmación de la nueva contraseña. |

### 4. Implementación

Para desarrollar esta funcionalidad se realizaron las siguientes acciones:

- Se creó `CambiarPasswordSerializer` para validar los datos recibidos.
- Se verifica que la contraseña actual sea correcta.
- Se comprueba que la nueva contraseña y su confirmación coincidan.
- Se valida la política de contraseñas configurada en Django.
- Se impide reutilizar la contraseña actual.
- Se utiliza el método `usuario.cambiar_password()` para actualizar la contraseña.
- Se creó `CambiarPasswordView` con el permiso `IsAuthenticated`.
- Se agregó la ruta correspondiente en las URLs de autenticación.

### 5. Respuesta exitosa

Cuando el cambio de contraseña se realiza correctamente, el endpoint devuelve una respuesta HTTP `200 OK`:

```json
{
    "mensaje": "Contraseña actualizada correctamente."
}
```

### 6. Consideraciones

- El endpoint requiere que el usuario tenga una sesión autenticada.
- No se utiliza el permiso `ContrasenaDefinitiva`, permitiendo cambiar contraseñas temporales.
- La emisión de nuevos tokens queda fuera del alcance de esta subtarea y corresponde a ST-113.

### 7. Dependencias

- HU-11: Cambiar mi contraseña con la sesión iniciada.
- ST-117: Método `Usuario.cambiar_password()`.
- ST-116: Configuración de permisos de autenticación.

**ST-112 finalizada.**

**Responsable de la actividad:** Alondra Alejandra López Medellin.