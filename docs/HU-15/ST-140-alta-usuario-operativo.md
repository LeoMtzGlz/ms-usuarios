# ST-140 - Endpoint de alta de usuario operativo

## Objetivo

Que un administrador registre a un trabajador, repartidor o conductor sin que tenga que registrarse él mismo
(HU-15). Esta subtarea crea el serializer y el endpoint; el aviso por correo es ST-142.

## Endpoint

`POST /api/v1/usuarios/` · permiso: `EsAdministrador` (más `IsAuthenticated` y `ContrasenaDefinitiva` de settings).

Cuerpo:

```json
{"nombre": "Luis", "apellidos": "Ramírez Soto", "correo": "luis@ejemplo.com", "telefono": "443 123 4567"}
```

Respuesta `201`:

```json
{
  "id": "…", "nombre": "Luis", "apellidos": "Ramírez Soto", "correo": "luis@ejemplo.com",
  "telefono": "+524431234567", "rol": "operativo", "estado": "activo",
  "debe_cambiar_password": true, "contrasena_temporal": "…"
}
```

`contrasena_temporal` se devuelve **una sola vez**: la base solo guarda su hash Argon2. La respuesta lleva
`Cache-Control: no-store`.

## Reglas

| Regla | Dónde |
| --- | --- |
| Correo (sin importar mayúsculas) y teléfono duplicados responden `400 datos_invalidos` con el campo | `AltaUsuarioSerializer` |
| Dos altas simultáneas las frena la restricción única de la base | `AltaUsuarioSerializer.create` |
| La cuenta nace activa, rol operativo y `debe_cambiar_password=True`; `rol`, `estado`, `password`... enviados por el cliente se ignoran | `AltaUsuarioSerializer.create` |
| Sin token `401`; cliente u operativo `403 sin_permiso`; administrador con contraseña temporal `403 debe_cambiar_password` | `AltaUsuarioView.permission_classes` |
| La bitácora registra `alta_usuario` con quién creó a quién y el rol, nunca la contraseña | `AltaUsuarioView.post` |

## Archivos

| Archivo | Cambio |
| --- | --- |
| `usuarios/serializers_admin.py` | `AltaUsuarioSerializer` |
| `usuarios/views_admin.py` | `AltaUsuarioView` |
| `usuarios/urls_admin.py` | Ruta `""` montada en `/api/v1/usuarios/` |
| `config/urls.py` | `include("usuarios.urls_admin")` |
| `usuarios/tests/test_alta_usuario.py` | Pruebas del endpoint |

## Pendiente en otras subtareas

- **ST-141:** `usuarios/contrasenas.py` ya trae un generador con `secrets` para que el endpoint funcione.
- **ST-142:** el aviso de cuenta creada se encola dentro de la transacción de `AltaUsuarioView.post`.
- **ST-143:** pruebas generales de HU-15.
- **HU-16:** el `GET` de listado se agrega en la misma ruta.
- **Login (ST-82):** `usuarios/tokens.py` ya agrega el claim `rol` al token y `EsAdministrador` lo lee, pero el endpoint de
  login todavía está en la rama `t-05/st-82`. Mientras no se integre no hay forma de obtener un token real; las pruebas
  lo emiten con `RefreshToken` y le ponen el claim a mano.
