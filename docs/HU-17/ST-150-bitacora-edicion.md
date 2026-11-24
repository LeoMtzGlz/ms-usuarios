# HU-17 — Editar los datos de un usuario

## ST-150 : Registrar los cambios en la bitácora

**Estado:** Terminada. En revisión (PR ```#96```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Registrar en la bitácora qué campos cambiaron y quién los cambió, sin guardar valores sensibles.

### Resultado: 
```usuarios/views_admin.py```, método ```perform_update``` de ```UsuarioDetalleView``` (la vista del ```PATCH /api/v1/usuarios/{id}/``` de st-149):
- Antes de guardar toma los valores de los campos de ```CAMPOS_EDITABLES``` (```nombre```, ```apellidos```, ```correo```, ```telefono```). Para leerlos usa el ```source``` de cada campo del serializer (```nombre``` → ```first_name```, ```apellidos``` → ```last_name```, ```correo``` → ```email```).
- Después de guardar compara y, si algo cambió, llama a:

```registrar_evento("usuario_editado", request.user, request, editado_id=str(usuario.pk), campos_cambiados=[...])```

- ```request.user``` → quién hizo la edición (mismo criterio que ```alta_usuario``` en HU-15).
- ```editado_id``` → a quién se editó.
- ```campos_cambiados``` → solo los **nombres** de los campos tal como los usa la API (por ejemplo ```["correo", "nombre"]```), nunca los valores anteriores ni los nuevos: correo y teléfono son datos personales.

Reglas:
- Si el PATCH no cambia nada, no se registra un evento vacío.
- Si la edición se rechaza (400), no se registra nada: ```serializer.save()``` falla antes de llegar a la bitácora.

Hoy ```registrar_evento()``` escribe en el log ```svc.auditoria```. Cuando HU-26 (st-188) guarde también en ```EventoAuditoria```, esta llamada no cambia.

### Pruebas: 
```usuarios/tests/test_edicion_usuario.py```, clase ```TestBitacora``` (4 pruebas; 23 passed en todo el archivo)
- ```test_bitacora_registra_quien_edito_y_que_campos``` → un solo evento ```usuario_editado``` con el ```usuario_id``` del admin, el ```editado_id``` y ```campos_cambiados``` = ```["correo", "nombre"]```.
- ```test_bitacora_no_guarda_los_valores``` → el correo y el nombre nuevos no aparecen en el log.
- ```test_sin_cambios_no_registra_evento``` → reenviar el mismo correo no genera evento.
- ```test_edicion_rechazada_no_registra_evento``` → un 400 (campo ```rol```) no deja evento.