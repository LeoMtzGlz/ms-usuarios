# HU-23 / ST-173 · Función `anonimizar_usuario()`

**Subtarea:** ID 173 · [Backend] Crear la función anonimizar_usuario()
**Historia padre:** HU-23 · Eliminar mi cuenta
**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)
**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-174
**Estado:** En revisión

## Descripción

Función que aplica el contrato de [ST-172](ST-172-datos-anonimizados.md): deja la cuenta sin datos personales, con valores genéricos únicos y la contraseña inutilizable (`set_unusable_password()`). La usa el endpoint `POST /api/v1/auth/eliminar-cuenta/` (ST-174).

## Resultado

`usuarios/anonimizacion.py`:

```python
from usuarios.anonimizacion import anonimizar_usuario

anonimizar_usuario(usuario, request=request, conservar_notificaciones=[confirmacion.pk])
```

| Parámetro | Para qué |
| --- | --- |
| `usuario` | La cuenta que se elimina |
| `request` | Opcional: para que el evento de la bitácora guarde la IP |
| `conservar_notificaciones` | Opcional: ids de notificaciones que no se tocan (el correo de confirmación que encola ST-174) |

Todo corre en **una sola transacción**: si algo falla, no se anonimiza nada. Es **irreversible**, y si la cuenta ya estaba anonimizada no hace nada (se puede llamar dos veces sin efectos extra).

## Qué hace

| Dato | Después de `anonimizar_usuario()` |
| --- | --- |
| `first_name`, `last_name` | `Usuario`, `eliminado` |
| `email` | `eliminado-<id>@anonimo.invalid` (único porque usa el id; `.invalid` nunca recibe correo) |
| `telefono` | `NULL` (libera el número) |
| `password` | `set_unusable_password()` |
| `estado`, `is_active` | `inactivo`, `False`, con `cambiar_estado()`, que además hace `token_version += 1` |
| Refresh tokens | Todos a la lista negra |
| `email_verificado`, `telefono_verificado`, `debe_cambiar_password` | `False` |
| `canal_preferido` | `correo` |
| `is_staff`, `is_superuser`, grupos, permisos | `False` y vacíos |
| `CodigoVerificacion`, `Dispositivo2FA` | Borrados |
| Notificaciones pendientes | Borradas, salvo las de `conservar_notificaciones` |
| Notificaciones enviadas o fallidas | Se conservan con `contexto = {}` |
| `AccessAttempt`, `AccessFailureLog`, `AccessLog` (django-axes) | Se borran las del correo original, sin importar mayúsculas |
| `id`, `rol`, `date_joined`, `last_login`, aceptación de privacidad | **Se conservan** |
| `RegistroAcceso` (HU-22), `EventoAuditoria` (HU-26) | **Se conservan** |

Al final registra el evento `cuenta_anonimizada`, sin el correo.

> `axes.utils.reset()` solo borra `AccessAttempt`; por eso la función borra las tres tablas de axes directamente.

## Lo que **no** hace (le toca a ST-174)

- Validar la contraseña y la palabra `ELIMINAR`.
- Impedir que se elimine el **único administrador**.
- Encolar el correo de confirmación y resolver que llegue al correo original (ST-172 §4.1).

## Pendiente de decidir

`eliminado_en` (ST-172 §1) no se agregó: toca `usuarios/models.py` y una migración, y el equipo no lo ha decidido. Mientras tanto, `esta_anonimizado(usuario)` permite saber si una cuenta fue eliminada (correo `@anonimo.invalid`).

## Pruebas

`usuarios/tests/test_anonimizacion.py`: 21 pruebas, una por cada fila de la tabla, más otros usuarios intactos, llamada repetida, transacción y evento.

```bash
docker compose exec api pytest usuarios/tests/test_anonimizacion.py -v
```