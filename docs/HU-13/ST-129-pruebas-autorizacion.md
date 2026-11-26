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
- Cliente y operativo reciben `403 sin_permiso` en auditoría y al desactivar o reactivar cuentas.
- Administrador obtiene `200` al listar y editar; un alta vacía llega a validación y responde `400 datos_invalidos`.
- Administrador obtiene `200` al consultar auditoría y al desactivar o reactivar cuentas.
- Administrador recibe `403 admin_requiere_2fa` al intentar desactivar 2FA; cliente y operativo superan esa
  autorización y llegan a la validación de datos.
- Los tres roles autenticados pueden aceptar el aviso de privacidad.
- `ContrasenaDefinitiva` bloquea todas las rutas protegidas salvo el cambio de contraseña.
- Los tres roles superan la autorización de 2FA y del cambio de contraseña.
- El rol administrador de la API no concede acceso al administrador de Django.
- El árbol real de rutas se obtiene mediante `get_resolver()` y cada combinación de ruta y método HTTP bajo
  `/api/` debe aparecer en la matriz.

## Rutas cubiertas

| Tipo | Rutas |
| --- | --- |
| Públicas | salud, registro, activación, login, renovación, reenvío, privacidad informativa, esquema y Swagger |
| Autenticadas | activar, confirmar y desactivar 2FA; aceptar privacidad; cambiar contraseña; historial de accesos |
| Solo administrador | auditoría; listado, alta, edición, desactivación y reactivación de usuarios |
| Administrador de Django | `/admin/`, controlado por `is_staff` y no por el rol del token |

## Criterio de mantenimiento

Cuando se integre un endpoint o un método nuevo, debe agregarse a esta matriz ejecutable con los casos aplicables:
sin token, rol incorrecto y rol correcto. Una operación pública nueva también debe incorporarse a
`RUTAS_PUBLICAS`; la prueba de resolución exigirá que su vista declare `AllowAny` explícitamente.

La comparación con el árbol real también hace fallar la suite si una combinación de método y ruta `/api/` se
agrega sin clasificarla como pública o protegida. Las rutas con UUID se normalizan para probarlas con un usuario
creado por la factory.

## Pendiente

El criterio "un cliente no puede ver datos de otro cliente" se probará cuando se integre el endpoint de perfil
(ST-163). El historial de accesos ya toma al propietario exclusivamente desde el token y no recibe otro usuario
como parámetro.
