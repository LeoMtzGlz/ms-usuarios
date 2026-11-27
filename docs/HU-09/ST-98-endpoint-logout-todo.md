# ST-98: Endpoint logout-todo

## Endpoint
POST /api/v1/auth/logout-todo/

## Descripción
HU-09: Cerrar sesión en todos mis dispositivos.

Incrementa `token_version` y registra `logout_todo` en la bitácora.

## Comportamiento
- Requiere autenticación.
- Incrementa `token_version += 1` de forma atómica.
- Como ST-90 compara `token_version` al renovar, ningún dispositivo puede renovar después.
- Nota: un `access` ya emitido sigue sirviendo hasta 15 minutos porque `JWTAuthentication` no revisa `token_version`. Solo el `refresh` queda inválido.