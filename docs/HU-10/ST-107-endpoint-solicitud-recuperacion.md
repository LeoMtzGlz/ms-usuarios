# ST-107: Crear el endpoint de solicitud de recuperación

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Descripción:** `POST /api/v1/auth/recuperar/` recibe el correo o teléfono de la cuenta y, si existe, envía un código de 6 dígitos (10 min, 5 intentos) para restablecer la contraseña.

## Petición
{"identificador": "ana@ejemplo.com", "canal": "correo"}

`identificador`: correo o teléfono (cualquier formato válido de México). `canal` es opcional (`correo` o `whatsapp`); si no se manda, se usa el preferido de la cuenta.

## Respuesta
Siempre `200` con `{"mensaje": "Si la cuenta existe, te enviamos un código."}`, exista o no la cuenta, para que nadie pueda saber quién está registrado. Errores de formato (falta `identificador`, `canal` inválido) devuelven `400 datos_invalidos`.

## Reglas
- Cuentas activas y pendientes reciben código; las inactivas y las inexistentes no (respuesta idéntica).
- Un nuevo pedido anula el código anterior.
- Si falla el envío se registra en el log y la respuesta no cambia.
- Para cuentas inexistentes se hace un hash de relleno, así el tiempo de respuesta es parecido.
- Se registra el evento `recuperacion_solicitada` sin guardar el código.
- Se agregó el alias `codigo_recuperacion` → `recuperacion_password` en `notificaciones/plantillas.py`.

## Archivos
`usuarios/recuperacion.py`, `usuarios/views_recuperacion.py`, `SolicitudRecuperacionSerializer`, ruta en `usuarios/urls.py`.
Restablecer la contraseña con el código es ST-108.

## Pruebas
docker compose run --rm api pytest usuarios/tests/test_recuperar.py -v