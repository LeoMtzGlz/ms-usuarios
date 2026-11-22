# ST-61 · Avisar en el registro por qué canal sale el código

**Historia:** HU-01 · Canal de envío del código
**Subtarea:** ST-61 · `canal_codigo` y `canal_sustituido` en el registro
**Estado:** terminada

## Qué es y para qué sirve

Al registrarse, la persona elige un canal (correo o WhatsApp). Si WhatsApp no está disponible, el código sale por correo. Antes el registro no lo decía, y la persona esperaba un mensaje que nunca llegaba por donde pensaba. Ahora la respuesta lo indica.

## Qué se hizo

- `RegistroView` se queda con el registro que devuelve `generar_codigo()` y lee de ahí el canal realmente usado.
- El 201 conserva todas sus claves y agrega dos:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `canal_codigo` | texto | `"correo"` o `"whatsapp"`: el canal por el que salió el código |
| `canal_sustituido` | booleano | `true` si ese canal no es el preferido de la persona |

```json
{
  "id": 7,
  "correo": "maria.hernandez@ejemplo.com",
  "canal_preferido": "whatsapp",
  "estado": "pendiente",
  "canal_codigo": "correo",
  "canal_sustituido": true
}
```

(Se muestran solo algunas claves; el resto no cambia.) El código nunca va en la respuesta.

- La documentación OpenAPI del registro menciona los dos campos.
- 6 pruebas nuevas en `usuarios/tests/test_canal_codigo.py`.

## Decisiones

- **El endpoint compara**, como texto, el canal usado contra el preferido. No se cambió `elegir_canal`, `crear_codigo` ni `generar_codigo`.
- **«No disponible» = WhatsApp sin teléfono**, que es lo que `elegir_canal` ya decide. No se consulta al proveedor.

## Qué no hace

- No toca el perfil (ST-60), la recuperación de contraseña ni al proveedor de mensajes.
- No cambia modelos, migraciones ni configuración.

## Cómo comprobarlo

```bash
docker compose run --rm api pytest usuarios/tests/test_canal_codigo.py -v
```

Con `canal_preferido: "whatsapp"` y teléfono, la respuesta trae `canal_codigo: "whatsapp"` y `canal_sustituido: false`.
