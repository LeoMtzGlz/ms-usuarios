# HU-02 — Registrarme como cliente

## ST-65 : [Backend] Crear RegistroSerializer con sus validaciones

**Estado:** En revisión.

**Responsable:** <tu nombre completo> (isis0015)

### Descripción
Serializer que valida los datos del registro de un cliente y crea su cuenta. Es la pieza que usará la vista `POST /api/v1/auth/registro/` (siguiente subtarea de HU-02).

### Resultado
`usuarios/serializers.py`, clase `RegistroSerializer`.

| Campo de la API | Campo del modelo | Reglas |
| --- | --- | --- |
| `nombre` | `first_name` | Obligatorio |
| `apellidos` | `last_name` | Obligatorio |
| `correo` | `email` | Obligatorio; se guarda sin espacios y en minúsculas; único sin importar mayúsculas |
| `telefono` | `telefono` | Obligatorio; se normaliza a E.164 (`443 123 4567` → `+524431234567`); único |
| `password` | `password` (hash) | `write_only`; debe cumplir `AUTH_PASSWORD_VALIDATORS` (T-12) |
| `password_confirmacion` | — | `write_only`; debe coincidir con `password` |
| `canal_preferido` | `canal_preferido` | `correo` o `whatsapp`; por defecto `correo` |
| `acepto_privacidad` | `acepto_privacidad_en`, `version_privacidad` | `write_only`; debe ser `true`, si no, la cuenta no se crea |

Al crear la cuenta:
- `estado = pendiente` y `rol = cliente`, aunque el cliente mande otros valores.
- `acepto_privacidad_en` guarda la fecha y hora del registro, y `version_privacidad` guarda `settings.VERSION_AVISO_PRIVACIDAD`.
- La contraseña se guarda con hash (Argon2), nunca en texto plano.
- Si dos registros con el mismo correo o teléfono llegan al mismo tiempo, la restricción única de la base frena el segundo y responde el mismo error de validación.

La respuesta (`serializer.data`) devuelve `id`, `nombre`, `apellidos`, `correo`, `telefono`, `canal_preferido`, `rol` y `estado`. Nunca incluye contraseñas ni tokens.

### Errores
Todos salen como `datos_invalidos` (400), con el detalle en `campos`:

| Campo | Mensaje |
| --- | --- |
| `correo` | `Este correo ya está registrado.` |
| `telefono` | `Este teléfono ya está registrado.` / `El teléfono no es un número válido.` |
| `password_confirmacion` | `Las contraseñas no coinciden.` |
| `password` | Los mensajes de la política de contraseñas (T-12) |
| `acepto_privacidad` | `Debes aceptar el aviso de privacidad para crear tu cuenta.` |

### Configuración nueva
| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `VERSION_AVISO_PRIVACIDAD` | `1.0` | Versión del aviso de privacidad vigente; se guarda en cada registro |

### Fuera del alcance de esta subtarea
La vista y la ruta `POST /api/v1/auth/registro/`, la respuesta 201 y el envío del código de activación corresponden a las siguientes subtareas de HU-02.

### Pruebas
`usuarios/tests/test_registro_serializer.py`:

```bash
docker compose run --rm api pytest usuarios/tests/test_registro_serializer.py -v
```