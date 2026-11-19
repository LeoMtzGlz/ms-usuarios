# ST-71 · Generar el código y encolarlo

**Historia:** HU-03 · Activar mi cuenta con un código
**Subtarea:** ST-71 · [Backend] Generar el código y encolarlo
**Autor:** Juan Diego Lomelí Coyazo (DiegoLC04) · **Revisora:** Katia Victoria (KPVE2004)

## Qué es y para qué sirve

Cuando una persona necesita un código de 6 dígitos (para activar su cuenta, recuperar la contraseña o cambiar su correo o teléfono), el sistema debe crearlo, guardarlo de forma segura y mandárselo por correo o WhatsApp. Esta subtarea reúne esos tres pasos en una sola función: `generar_codigo()`.

## Punto de partida

`usuarios/codigos.py` lo creó Isis en HU-02 / ST-66 con una versión mínima, para poder registrar cuentas. El profesor pidió que ST-71 parta de ese archivo. Esta subtarea lo completa.

## Qué se hizo

- `generar_codigo(usuario, proposito, canal=None)` ahora crea el código **y encola la notificación** en una sola transacción. Devuelve el registro, nunca el código en claro.
- El sorteo de los 6 dígitos pasó a llamarse `sortear_codigo()`, porque `generar_codigo` es ahora el punto de entrada.
- Los minutos de vigencia salen de `settings.CODIGO_MINUTOS` (por defecto 10, configurable con la variable de entorno `CODIGO_MINUTOS`).
- Si el canal es WhatsApp y la persona no tiene teléfono, se usa correo.
- `RegistroView` llama a `generar_codigo()` en lugar de llamar por separado a `crear_codigo()` y a `notificar()`.
- En la prueba de Isis (`test_registro_endpoint.py`) se actualizaron dos rutas de `mock.patch`, porque `notificar` y `crear_codigo` ya no se usan en la vista sino en `usuarios.codigos`. La prueba sigue comprobando lo mismo.
- 13 pruebas nuevas en `usuarios/tests/test_codigos.py`.

## Funciones de `usuarios/codigos.py`

| Función | Qué hace |
| --- | --- |
| `sortear_codigo()` | 6 dígitos con ceros a la izquierda, con `secrets.randbelow` |
| `elegir_canal(usuario, canal=None)` | Canal indicado o el preferido; WhatsApp sin teléfono pasa a correo; un canal desconocido lanza `ValueError` |
| `crear_codigo(usuario, proposito, canal=None)` | Anula los códigos pendientes, guarda el hash y devuelve `(registro, codigo_en_claro)` |
| `generar_codigo(usuario, proposito, canal=None)` | Llama a `crear_codigo()` y a `notificar()` dentro de `transaction.atomic()` |

## Decisiones

- **Solo se guarda el hash** (`make_password`). El código en claro existe únicamente en memoria y en el mensaje.
- **Una sola transacción.** Si falla el encolado, tampoco queda el código.
- **Un código nuevo anula los anteriores** pendientes del mismo propósito. Es una decisión de esta subtarea, no está en el backlog.
- **Una plantilla por propósito:** `codigo_activacion`, `codigo_recuperacion` y `codigo_cambio_contacto`.
- **Canal desconocido:** se rechaza antes de crear nada, porque `notificar()` no valida el canal.

## Nota de seguridad

El código en claro viaja en el campo `contexto` de la notificación pendiente hasta que se envía. Según el criterio de T-07, el worker (T-10) debe vaciar ese campo al enviar o al vencer. En la tabla de códigos solo hay hash.

## Qué no hace

No valida el código ni cuenta intentos. Eso es ST-72 (endpoint de activación). Las pruebas del endpoint son ST-73.

## Cómo comprobarlo

```bash
docker compose exec api pytest usuarios/tests/test_codigos.py -v
docker compose exec api pytest -q
docker compose exec api ruff check .
```
