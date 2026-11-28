# T-11 — Controlar las cuotas gratuitas de cada canal

## ST-57. Aplicar el límite antes de enviar

**Estado:** En revisión
**Responsable:** l22420429

### 1. Descripción

El worker de notificaciones (T-10/ST-51) revisa el límite diario de cada canal antes de enviar,
usando el conteo de ST-56 (`contar_envios_hoy()`):

- **WhatsApp al límite:** la notificación cambia a correo y sale por ahí en el mismo ciclo.
- **Correo al límite:** la notificación queda `pendiente` y sale al día siguiente, cuando el conteo
  vuelve a empezar. Se registra una advertencia en el log (`svc.notificaciones`), una vez por canal y
  por día.
- **WhatsApp y correo al límite:** la de WhatsApp también espera al día siguiente.
- **Consola** no tiene límite.

Las pruebas de estos casos son ST-58.

### 2. Configuración

| Variable del `.env` | Por defecto | Qué es |
|---|---|---|
| `LIMITE_DIARIO_CORREO` | `500` | Envíos de correo por día. Gmail permite 500; con Brevo usar 300. |
| `LIMITE_DIARIO_WHATSAPP` | `250` | Envíos de WhatsApp por día (límite inicial de Meta en cuentas nuevas). |

Si la variable no está en el `.env`, se usa el valor por defecto.

### 3. Cambios realizados

| Archivo | Cambio |
|---|---|
| `config/settings.py` | `LIMITE_DIARIO_CORREO` y `LIMITE_DIARIO_WHATSAPP` (con `env.int`). |
| `.env.example` | Las dos variables nuevas con su comentario. |
| `notificaciones/worker.py` | `LIMITES_DIARIOS`, `limite_alcanzado()`, `avisar_limite()`, `canales_en_espera()`; lógica en `antes_de_enviar()`; `tomar_pendientes()` acepta `excluir_canales`; `procesar_lote()` excluye los canales en espera. |
| `docs/T-11/ST-57-aplicar-limite-antes-de-enviar.md` | Esta documentación. |

No se tocaron modelos ni migraciones.

### 4. Cómo funciona

1. Al inicio de cada lote, `procesar_lote()` llama a `canales_en_espera()`. Si el correo ya llegó a
   su límite, el lote no toma notificaciones de correo; si además WhatsApp llegó al suyo, tampoco toma
   las de WhatsApp. Así las pospuestas no ocupan los 20 lugares del lote y no bloquean a los canales
   que sí tienen cupo.
2. Para cada notificación, `procesar()` llama a `antes_de_enviar()`, que vuelve a revisar el límite
   por si se alcanzó a mitad del lote:
   - WhatsApp al límite y correo con cupo: cambia `canal` a correo y lo guarda. `procesar()` usa ese
     canal para el destino (`destino_de`) y para el envío (`obtener_canal`), así que el envío cuenta
     para el límite del correo.
   - Correo al límite: devuelve `False` y la notificación cuenta como `pospuesta`.
3. `LIMITES_DIARIOS` guarda el **nombre** del setting y no su valor: el límite se lee en cada
   revisión, así funciona `@override_settings` en las pruebas.

### 5. Decisiones y limitaciones

- **Una pospuesta no suma intentos** ni cambia su `creado_en`: al día siguiente conserva su lugar en
  la fila.
- **Códigos vencidos:** una notificación con código que espera al día siguiente normalmente ya
  venció. `procesar()` la marca `fallida` sin enviarla (regla de T-10), así que no se reenvía un
  código vencido.
- **Advertencia una vez al día:** el registro de avisos vive en memoria de cada worker. Si se
  reinicia el worker o hay dos workers, cada uno puede avisar una vez.
- **Varios workers:** dos workers pueden revisar el conteo al mismo tiempo y pasarse por unos pocos
  envíos del límite. Los valores por defecto ya dejan ese margen bajo el tope real del proveedor.
- **Fecha de envío:** el conteo usa `actualizado_en` (ver la limitación de ST-56). Al cambiar una
  notificación de WhatsApp a correo se guarda `actualizado_en`, pero la notificación todavía está
  `pendiente`, así que no afecta el conteo.

### 6. Verificación

```bash
docker compose run --rm api ruff check .
docker compose run --rm api python manage.py makemigrations --check --dry-run
docker compose run --rm api pytest
```
