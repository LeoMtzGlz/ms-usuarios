# ST-164 - Verificar el correo o teléfono nuevo con código

## Resultado

Se completó el cambio verificado del correo o teléfono del usuario autenticado. El contacto actual permanece sin cambios hasta que la persona confirma un código de seis dígitos enviado al dato nuevo.

## Endpoints

### Solicitar el cambio

`POST /api/v1/auth/perfil/contacto/solicitar/`

```json
{
  "tipo": "correo",
  "valor": "nuevo@ejemplo.com",
  "password": "contraseña actual"
}
```

Para un teléfono, `tipo` es `telefono`; el valor se normaliza a E.164. La solicitud exige sesión autenticada, contraseña definitiva y la contraseña actual correcta. También comprueba que el contacto sea distinto y que no pertenezca a otra cuenta.

### Confirmar el cambio

`POST /api/v1/auth/perfil/contacto/confirmar/`

```json
{
  "tipo": "correo",
  "valor": "nuevo@ejemplo.com",
  "codigo": "123456"
}
```

La confirmación debe repetir exactamente el tipo y el contacto solicitado. Si el código es válido, vigente y no ha superado cinco intentos, el dato se actualiza y su indicador de verificación queda activo.

## Seguridad

- Se usa `CodigoVerificacion` con el propósito `cambio_contacto`.
- La base de datos conserva únicamente un hash que liga código, tipo y contacto normalizado.
- Un código interceptado no sirve para confirmar un contacto diferente.
- Cada solicitud nueva anula el código anterior pendiente.
- El código vence según `CODIGO_MINUTOS`, admite como máximo cinco intentos y es de un solo uso.
- El contacto nuevo solo permanece temporalmente en la notificación pendiente; el worker elimina el contexto al enviarla o descartarla.
- Los eventos de auditoría registran el tipo de cambio, pero no el código, la contraseña ni el contacto nuevo.

## Relación

Completa la segunda parte de HU-21 después de ST-163. ST-165 ampliará las pruebas de aceptación de edición correcta, dato duplicado y conservación del contacto mientras no se confirme el código.
