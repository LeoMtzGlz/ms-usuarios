# ST-112 - Endpoint para cambiar contraseña

## Objetivo

Implementar el endpoint que permite a un usuario autenticado cambiar su contraseña actual por una nueva.

## Endpoint

`POST /api/v1/auth/cambiar-password/`

## Datos de entrada

| Campo | Descripción |
|---|---|
| password_actual | Contraseña actual del usuario |
| password_nueva | Nueva contraseña |
| password_confirmacion | Confirmación de la nueva contraseña |

## Implementación

- Se creó `CambiarPasswordSerializer` para validar los datos recibidos.
- Se verifica que la contraseña actual sea correcta.
- Se comprueba que la nueva contraseña y su confirmación coincidan.
- Se valida la política de contraseñas configurada en Django.
- Se impide reutilizar la contraseña actual.
- Se utiliza el método `usuario.cambiar_password()` para actualizar la contraseña.
- Se creó `CambiarPasswordView` con el permiso `IsAuthenticated`.
- Se agregó la ruta correspondiente en las URLs de autenticación.

## Respuesta exitosa

Código HTTP: `200 OK`

```json
{
    "mensaje": "Contraseña actualizada correctamente."
}
```

## Consideraciones

- El endpoint requiere autenticación.
- No se utiliza el permiso `ContrasenaDefinitiva`, permitiendo cambiar contraseñas temporales.
- La emisión de nuevos tokens queda fuera del alcance de esta subtarea y corresponde a ST-113.

## Dependencias

- HU-11: Cambiar mi contraseña con la sesión iniciada.
- ST-117: Método `Usuario.cambiar_password()`.
- ST-116: Configuración de permisos de autenticación.