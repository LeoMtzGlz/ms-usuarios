# ST-132 · Registrar el cambio de rol en la bitácora

- **Historia de usuario:** HU-14 · Cambiar el rol de un usuario
- **Rama:** `t-14/st-132`
- **Responsable:** Daniel Orlando Ceja Olloqui (`l22420448@jiquilpan.tecnm.mx`)

## Objetivo

Registrar un evento de auditoría (`rol_cambiado`) en la bitácora cada vez que un administrador modifique el rol de un usuario mediante `PATCH /api/v1/usuarios/{id}/rol/`, dejando constancia del administrador que realizó el cambio, la marca de tiempo, el usuario afectado y los roles anterior y nuevo.

## Cambios realizados

1. **`usuarios/views_admin.py` (`CambiarRolView.patch`):**
   - Cuando `usuario.rol != nuevo_rol`, se conserva `rol_anterior` antes de actualizar el registro.
   - Tras guardar el nuevo rol e incrementar `token_version`, se invoca `registrar_evento("rol_cambiado", request.user, request, usuario_id=str(usuario.pk), rol_anterior=rol_anterior, rol_nuevo=nuevo_rol)`.
   - Si el administrador envía el mismo rol que el usuario ya poseía, no se modifica el registro ni se genera un evento duplicado en la bitácora.

## Estructura del evento registrado

- **`accion`:** `"rol_cambiado"`
- **`usuario`:** administrador autenticado que ejecutó la petición (`request.user`)
- **`resultado`:** `"ok"`
- **`detalles`:**
  ```json
  {
    "usuario_id": "<uuid-del-usuario-afectado>",
    "rol_anterior": "cliente",
    "rol_nuevo": "operativo"
  }
  