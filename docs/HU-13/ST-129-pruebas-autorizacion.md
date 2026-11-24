# ST-129 - Pruebas de autorización

## Objetivo

Convertir la matriz endpoint por rol de ST-127 en pruebas automáticas sobre las rutas que ya existen en
`development`. Las rutas planeadas se probarán cuando su implementación se integre.

## Cobertura

- Las rutas públicas responden sin exigir autenticación.
- Toda vista pública declara `AllowAny` de forma explícita.
- Las rutas protegidas responden `401 no_autenticado` sin token.
- Cliente y operativo reciben `403 sin_permiso` en la administración de usuarios.
- Cliente y operativo reciben `403 sin_permiso` al intentar editar un usuario.
- Administrador obtiene `200` al listar y editar; un alta vacía llega a validación y responde `400 datos_invalidos`.
- Los tres roles autenticados pueden aceptar el aviso de privacidad.
- `ContrasenaDefinitiva` bloquea todas las rutas protegidas salvo el cambio de contraseña.
- Los tres roles superan la autorización de 2FA y del cambio de contraseña.
- El rol administrador de la API no concede acceso al administrador de Django.
- El árbol real de rutas se obtiene mediante `get_resolver()` y toda ruta `/api/` debe aparecer en la matriz.

## Rutas cubiertas

| Tipo | Rutas |
| --- | --- |
| Públicas | salud, registro, login, privacidad informativa, esquema y Swagger |
| Autenticadas | activar 2FA, confirmar 2FA, aceptar privacidad y cambiar contraseña |
| Solo administrador | listado, alta y edición de usuarios mediante `PATCH /api/v1/usuarios/<uuid>/` |
| Administrador de Django | `/admin/`, controlado por `is_staff` y no por el rol del token |

## Criterio de mantenimiento

Cuando se integre un endpoint nuevo, debe agregarse a esta matriz ejecutable con los casos aplicables: sin token,
rol incorrecto y rol correcto. Una ruta pública nueva también debe incorporarse a `RUTAS_PUBLICAS`; la prueba de
resolución exigirá que declare `AllowAny` explícitamente.

La comparación con el árbol real también hace fallar la suite si una ruta `/api/` se agrega sin clasificarla como
pública o protegida. Las rutas con UUID se normalizan para probarlas con un usuario creado por la factory.

## Pendiente

El criterio "un cliente no puede ver datos de otro cliente" se probará cuando existan los endpoints de perfil
(ST-163) y accesos (ST-168), porque las rutas disponibles todavía no exponen recursos pertenecientes a otro cliente.
