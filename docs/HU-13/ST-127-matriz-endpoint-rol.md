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
| `POST` | `/api/v1/auth/login/` | En rama | Sí | Sí | Sí | Sí | `AllowAny` | HU-05 / ST-82 |
| `GET` | `/api/v1/auth/privacidad/` | En PR #60 | Sí | Sí | Sí | Sí | `AllowAny` | HU-29 / ST-201 |
| `POST` | `/api/v1/auth/privacidad/aceptar/` | En PR #60 | No | Sí | Sí | Sí | `IsAuthenticated` | HU-29 / ST-201 |
| `POST` | `/api/v1/auth/activar/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | HU-03 / ST-72 |
| `POST` | `/api/v1/auth/reenviar-codigo/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | HU-04 / ST-75 |
| `POST` | `/api/v1/auth/token/renovar/` | Planeado | Sí² | Sí | Sí | Sí | Token de renovación válido | HU-06 |
| `POST` | `/api/v1/auth/logout/` | Planeado | No | Sí | Sí | Sí | `IsAuthenticated` | HU-08 |
| `POST` | `/api/v1/auth/logout-todo/` | Planeado | No | Sí | Sí | Sí | `IsAuthenticated` | HU-09 |
| `POST` | `/api/v1/auth/recuperar/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | HU-10 |
| `POST` | `/api/v1/auth/restablecer/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | HU-10 |
| `POST` | `/api/v1/auth/cambiar-password/` | Planeado | No | Sí | Sí | Sí | Propietario autenticado | HU-11 / ST-112 |
| `GET` | `/api/v1/auth/llave-publica/` | Planeado | Sí | Sí | Sí | Sí | `AllowAny` | T-14 / ST-135 |
| `GET`, `PATCH` | `/api/v1/auth/perfil/` | Planeado | No | Sí | Sí | Sí | Propietario autenticado | HU-21 / ST-163 |
| `GET` | `/api/v1/auth/accesos/` | Planeado | No | Sí | Sí | Sí | Propietario autenticado | HU-22 / ST-168 |
| `POST` | `/api/v1/auth/eliminar-cuenta/` | Planeado | No | Sí | Sí | Sí³ | Propietario autenticado | HU-23 / ST-174 |
| `GET`, `POST` | `/api/v1/usuarios/` | Planeado | No | No | No | Sí | `EsAdministrador` | HU-15 / HU-16 |
| `PATCH` | `/api/v1/usuarios/{id}/` | Planeado | No | No | No | Sí | `EsAdministrador` | HU-17 / ST-149 |
| `PATCH` | `/api/v1/usuarios/{id}/rol/` | Planeado | No | No | No | Sí | `EsAdministrador` | HU-14 / ST-131 |
| `GET` | `/api/v1/auditoria/` | En rama | No | No | No | Sí | `EsAdministrador` | HU-26 / ST-189 |

¹ El rol de dominio no concede acceso a `/admin/`; Django exige `is_staff=True`.

² El cliente no envía un token de acceso, pero sí un token de renovación válido.

³ HU-23 impide que el único administrador elimine su propia cuenta.

## Operaciones con ruta por confirmar

Estas historias sí requieren autorización en ST-128, pero el backlog no fija una URL completa. No se inventa una ruta
en la matriz: debe confirmarse con quien implemente cada historia.

| Operación | Acceso esperado | Fuente |
| --- | --- | --- |
| Desactivar o reactivar una cuenta | Solo administrador | HU-18 / ST-153 |
| Restablecer la contraseña temporal de un operativo | Solo administrador | HU-19 / ST-156 |
| Desbloquear una cuenta | Solo administrador | HU-20 / ST-159 |
| Activar y confirmar 2FA | Propietario autenticado | HU-30 / ST-206 |
| Verificar el segundo factor durante el login | Token temporal de 2FA | HU-31 / ST-211 |
| Desactivar 2FA | Cliente u operativo propietario; no administrador | HU-32 / ST-215 |

## Regla para actualizarla

Cuando una ruta planeada se integre, se debe confirmar su URL y su `permission_classes`, cambiar su estado a
**Disponible** y ajustar la matriz del `README.md`. ST-129 debe convertir cada combinación permitida y denegada en
pruebas de autorización.
