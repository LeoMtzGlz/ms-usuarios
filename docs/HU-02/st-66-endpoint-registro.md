# HU-02 — Registrarme como cliente

## ST-66 : [Backend] Crear el endpoint con transacción

**Estado:** En revisión.

**Responsable:** <Isis Lizbeth Vazquez Avalos> (isis0015)

### Descripción
Endpoint público `POST /api/v1/auth/registro/` que crea la cuenta de un cliente y encola su código de activación, todo dentro de una sola transacción.

### Resultado

| Archivo | Qué contiene |
| --- | --- |
| `usuarios/views.py` | `RegistroView` |
| `usuarios/urls.py` | Ruta `registro/` (nombre `auth:registro`) |
| `config/urls.py` | Monta `usuarios.urls` en `/api/v1/auth/` |
| `usuarios/codigos.py` | `generar_codigo()` y `crear_codigo()` |

Flujo de `RegistroView.post()`:

1. `RegistroSerializer` valida los datos (ST-65). Si algo falla, responde **400** `datos_invalidos` y no se crea nada.
2. Abre `transaction.atomic()` y dentro:
   - `serializer.save()` → `Usuario.objects.create_user(...)`: cuenta **pendiente**, rol **cliente**.
   - `crear_codigo(usuario, Proposito.ACTIVACION)`: código de 6 dígitos, guardado solo con hash, vigente 10 minutos.
   - `notificar(usuario, "codigo_activacion", {...})`: deja el aviso en la bandeja de salida, por el `canal_preferido` de la persona.
3. Registra el evento `registro` en la bitácora.
4. Responde **201** con los datos públicos de la cuenta. **Sin tokens**: la sesión empieza hasta activar la cuenta (HU-03).

### Decisiones
- **Una sola transacción.** Si falla el código o la notificación, se deshace todo: no queda una cuenta sin código para activarla.
- **`AllowAny` y sin clases de autenticación.** Es un endpoint público; si el cliente manda un token viejo, no debe responder 401.
- **`notificar()` solo encola.** El envío real por correo o WhatsApp lo hace el proceso de la bandeja de salida (T-07), fuera de la petición.
- **Contexto de la plantilla `codigo_activacion`:** `codigo`, `nombre` y `minutos` (vigencia).

### Coordinación con HU-03
`usuarios/codigos.py` incluye solo lo mínimo para crear el código. La verificación (validar el código, contar intentos, expirar) es de **HU-03 (ST-71/ST-72)**, que debe reutilizar y ampliar este mismo archivo en lugar de crear otro.

### Ejemplo
```bash
curl -X POST http://localhost:8000/api/v1/auth/registro/ \
  -H "Content-Type: application/json" \
  -d '{"nombre": "María", "apellidos": "Hernández Ruiz", "correo": "maria@ejemplo.com",
       "telefono": "443 123 4567", "password": "Registro2026", "password_confirmacion": "Registro2026",
       "canal_preferido": "correo", "acepto_privacidad": true}'
```

Respuesta `201`:
```json
{"id": "…", "nombre": "María", "apellidos": "Hernández Ruiz", "correo": "maria@ejemplo.com",
 "telefono": "+524431234567", "canal_preferido": "correo", "rol": "cliente", "estado": "pendiente"}
```

### Pruebas
`usuarios/tests/test_registro_endpoint.py`: 201 sin tokens, cuenta pendiente de cliente, código con hash, notificación encolada, endpoint público, errores 400, solo POST y rollback si falla el código o la notificación.

```bash
docker compose run --rm api pytest usuarios/tests/test_registro_endpoint.py -v
```