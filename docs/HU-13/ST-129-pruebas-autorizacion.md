# ST-129 - Pruebas de autorización

## Objetivo

Convertir la matriz endpoint por rol de ST-127 en pruebas automáticas sobre las rutas que ya existen en
`development`. Las rutas planeadas se probarán cuando su implementación se integre.

## Cobertura

- Las rutas públicas responden sin exigir autenticación.
- Toda vista pública declara `AllowAny` de forma explícita.
- Las rutas protegidas responden `401 no_autenticado` sin token.
- Cliente y operativo reciben `403 sin_permiso` en la administración de usuarios.
- Administrador supera la autorización para listar y crear usuarios.
- Los tres roles autenticados pueden aceptar el aviso de privacidad.
- El rol administrador de la API no concede acceso al administrador de Django.
- El árbol real de rutas se obtiene mediante `get_resolver()` para detectar omisiones futuras.

## Rutas cubiertas

| Tipo | Rutas |
| --- | --- |
| Públicas | salud, registro, login, privacidad informativa, esquema y Swagger |
| Autenticadas | activar 2FA, confirmar 2FA y aceptar privacidad |
| Solo administrador | listado y alta de usuarios |
| Administrador de Django | `/admin/`, controlado por `is_staff` y no por el rol del token |

## Criterio de mantenimiento

Cuando se integre un endpoint nuevo, debe agregarse a esta matriz ejecutable con los casos aplicables: sin token,
rol incorrecto y rol correcto. Una ruta pública nueva también debe incorporarse a `RUTAS_PUBLICAS`; la prueba de
resolución exigirá que declare `AllowAny` explícitamente.
