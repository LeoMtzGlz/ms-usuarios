# ST-127 · Matriz endpoint × rol

## Objetivo

Mantener una sola referencia de autorización para ST-128 y ST-129. La matriz distingue las rutas disponibles de las
que todavía están en revisión, en una rama o planeadas en el backlog. Incluir una ruta aquí no significa que ya esté
implementada.

## Estados

| Estado | Significado |
| --- | --- |
| Disponible | La ruta existe en `development`. |
| En PR | La ruta está propuesta en un Pull Request abierto y puede cambiar antes de integrarse. |
| En rama | La ruta existe en una rama de trabajo, pero todavía no está en `development`. |
| Planeado | El backlog define la ruta, pero aún no está implementada. |
| Ruta por confirmar | El backlog pide la operación, pero no fija su URL; el equipo debe acordarla antes de ST-128. |

## Matriz

| Método | Ruta | Estado | Sin token | Cliente | Operativo | Administrador | Permiso esperado | Fuente |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/api/v1/salud/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | T-01 |
| `POST` | `/api/v1/auth/registro/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-02 / ST-66 |
| `GET` | `/api/schema/` | Disponible | Sí | Sí | Sí | Sí | Pública (`drf-spectacular`) | T-05 |
| `GET` | `/api/docs/` | Disponible | Sí | Sí | Sí | Sí | Pública (`drf-spectacular`) | T-05 |
| `GET`, `POST` | `/admin/` y sus rutas internas | Disponible | No | No¹ | No¹ | No¹ | `is_staff` de Django | T-02 |
| `POST` | `/api/v1/auth/login/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-05 / ST-82 |
| `POST` | `/api/v1/auth/google/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-33 / ST-219 |
| `GET` | `/api/v1/auth/privacidad/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-29 / ST-201 |
| `POST` | `/api/v1/auth/privacidad/aceptar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` | HU-29 / ST-201 |
| `POST` | `/api/v1/auth/2fa/activar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` | HU-30 / ST-206 |
| `POST` | `/api/v1/auth/2fa/confirmar/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` + `ContrasenaDefinitiva` | HU-30 / ST-206 |
| `POST` | `/api/v1/auth/2fa/desactivar/` | Disponible | No | Sí | Sí | No | `IsAuthenticated` + `ContrasenaDefinitiva` | HU-32 / ST-215 |
| `POST` | `/api/v1/auth/activar/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-03 / ST-72 |
| `POST` | `/api/v1/auth/reenviar-codigo/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-04 / ST-75 |
| `POST` | `/api/v1/auth/token/renovar/` | Disponible | Sí² | Sí | Sí | Sí | `AllowAny` + token de renovación válido | HU-07 / ST-90 |
| `POST` | `/api/v1/auth/logout/` | Planeado | No | Sí | Sí | Sí | `IsAuthenticated` | HU-08 |
| `POST` | `/api/v1/auth/logout-todo/` | Planeado | No | Sí | Sí | Sí | `IsAuthenticated` | HU-09 |
| `POST` | `/api/v1/auth/recuperar/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-10 / ST-107 |
| `POST` | `/api/v1/auth/restablecer/` | Disponible | Sí | Sí | Sí | Sí | `AllowAny` | HU-10 / ST-108 |
| `POST` | `/api/v1/auth/cambiar-password/` | Disponible | No | Sí | Sí | Sí | `IsAuthenticated` (exenta de `ContrasenaDefinitiva`) | HU-11 / ST-112 |
| `GET` | `/api/v1/auth/llave-publica/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | T-14 / ST-135 |
| `GET`, `PATCH` | `/api/v1/auth/perfil/` | Disponible | No | Sí | Sí | Sí | Propietario autenticado | HU-21 / ST-163 |
| `GET` | `/api/v1/auth/accesos/` | Disponible | No | Sí | Sí | Sí | Propietario autenticado | HU-22 / ST-168 |
| `POST` | `/api/v1/auth/eliminar-cuenta/` | Planeado | No | Sí | Sí | Sí³ | Propietario autenticado | HU-23 / ST-174 |
| `GET`, `POST` | `/api/v1/usuarios/` | Disponible | No | No | No | Sí | `EsAdministrador` | HU-15 / HU-16 |
| `PATCH` | `/api/v1/usuarios/{id}/` | Disponible | No | No | No | Sí | `EsAdministrador` | HU-17 / ST-149 |
| `POST` | `/api/v1/usuarios/{id}/desactivar/` | Disponible | No | No | No | Sí | `EsAdministrador` | HU-18 / ST-153 |
| `POST` | `/api/v1/usuarios/{id}/reactivar/` | Disponible | No | No | No | Sí | `EsAdministrador` | HU-18 / ST-153 |
| `PATCH` | `/api/v1/usuarios/{id}/rol/` | Planeado | No | No | No | Sí | `EsAdministrador` | HU-14 / ST-131 |
| `GET` | `/api/v1/auditoria/` | Disponible | No | No | No | Sí | `EsAdministrador` | HU-26 / ST-189 |

¹ El rol de dominio no concede acceso a `/admin/`; Django exige `is_staff=True`.

² El cliente no envía un token de acceso, pero sí un token de renovación válido.

³ HU-23 impide que el único administrador elimine su propia cuenta.

## Operaciones con ruta por confirmar

Estas historias sí requieren autorización en ST-128, pero el backlog no fija una URL completa. No se inventa una ruta
en la matriz: debe confirmarse con quien implemente cada historia.

| Operación | Acceso esperado | Fuente |
| --- | --- | --- |
| Restablecer la contraseña temporal de un operativo | Solo administrador | HU-19 / ST-156 |
| Desbloquear una cuenta | Solo administrador | HU-20 / ST-159 |
| Verificar el segundo factor durante el login | Token temporal de 2FA | HU-31 / ST-211 |

## Regla para actualizarla

Cuando una ruta planeada se integre, se debe confirmar su URL y su `permission_classes`, cambiar su estado a
**Disponible** y ajustar la matriz del `README.md`. ST-129 debe convertir cada combinación permitida y denegada en
pruebas de autorización.