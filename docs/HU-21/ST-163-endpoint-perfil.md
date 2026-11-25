# HU-21 / ST-163 - Endpoint de perfil propio

## Objetivo

Permitir que cualquier cliente, operativo o administrador autenticado consulte y actualice sus datos básicos mediante
`GET` y `PATCH /api/v1/auth/perfil/`, sin aceptar un identificador de usuario en la URL.

## Contrato

La respuesta contiene `id`, `nombre`, `apellidos`, `correo`, `telefono`, `canal_preferido`, `rol` y `estado`. No expone
la contraseña, la versión de los tokens, indicadores internos de Django ni datos de 2FA.

En esta subtarea solamente se pueden editar:

- `nombre`
- `apellidos`
- `canal_preferido`

`WhatsApp` solo puede seleccionarse si la cuenta ya tiene un teléfono registrado. Si no lo tiene, el endpoint
responde `400 datos_invalidos` y conserva el canal anterior.

El correo y el teléfono son de solo lectura. Su modificación requiere contraseña y un código enviado al contacto nuevo;
ese proceso corresponde a ST-164. También se rechaza cualquier intento de cambiar el rol, el estado, la contraseña u
otro campo interno desde este endpoint.

## Seguridad

- La vista hereda `IsAuthenticated` y `ContrasenaDefinitiva` de la configuración global.
- El objeto siempre es `request.user`; no existe un parámetro con el cual solicitar el perfil de otra persona.
- Los tres roles consultan y editan únicamente su propio perfil.
- `PUT` y `DELETE` no están habilitados.

## Pruebas

`usuarios/tests/test_perfil.py` comprueba la consulta para los tres roles, la edición parcial, la lista blanca de campos,
la regla de WhatsApp con teléfono, la ausencia de datos sensibles, los métodos rechazados y las respuestas `401` y
`403` correspondientes.
