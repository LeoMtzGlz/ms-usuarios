# HU-17 — Editar los datos de un usuario

## ST-149 : Crear el endpoint de edición

**Estado:** Terminada. En revisión (PR ```t-17/st-149: Crear el endpoint de edición```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Endpoint para que un administrador edite los datos de contacto de un usuario.
- ```PATCH /api/v1/usuarios/{id}/``` edita nombre, apellidos, correo y teléfono.
- No permite cambiar la contraseña ni el rol por aquí.
- Valida duplicados sin contar al propio usuario (```exclude(pk=...)```).

### Resultado:
- ```usuarios/serializers_admin.py```: ```EdicionUsuarioSerializer```
  - Campos editables: ```nombre```, ```apellidos```, ```correo``` y ```telefono``` (los mismos nombres que el alta de HU-15), guardados en ```first_name```, ```last_name```, ```email``` y ```telefono```.
  - Lista blanca: cualquier otro campo (```password```, ```rol```, ```estado```, ```debe_cambiar_password```, ```token_version```…) responde 400 con un mensaje por campo.
  - Correo: se normaliza a minúsculas y se rechaza si otra cuenta lo tiene, sin importar mayúsculas (```email__iexact``` + ```exclude(pk=...)```).
  - Teléfono: se normaliza con ```normalizar_telefono()``` (```usuarios/telefono.py```) y se rechaza si otra cuenta lo tiene.
  - Mensajes de duplicado: ```CORREO_REGISTRADO``` y ```TELEFONO_REGISTRADO``` (```usuarios/serializers.py```).
  - Si dos ediciones compiten, el ```IntegrityError``` de la restricción única se convierte en 400.
- ```usuarios/views_admin.py```: ```EdicionUsuarioView``` con ```permission_classes = permisos_por_defecto_mas(EsAdministrador)```; solo acepta ```PATCH```; 404 si el usuario no existe. Responde 200 con los mismos datos públicos que el alta (sin contraseña).
- ```usuarios/urls_admin.py```: ruta ```<uuid:pk>/```.

### Decisiones:
- A diferencia del alta (que ignora campos extra), la edición **rechaza** los campos no editables con 400, porque el criterio dice que no se permite cambiarlos por aquí y así el cliente sabe que no se aplicaron.
- No hay ```DELETE```: los usuarios no se borran (HU-18).

### Pruebas:
- ```usuarios/tests/test_edicion_usuario.py``` (<N> passed)
- ```test_edicion_parcial_cambia_solo_lo_enviado``` → un PATCH con un campo no toca los demás.
- ```test_edita_nombre_apellidos_correo_y_telefono``` → los cuatro campos se guardan en el modelo.
- ```test_normaliza_correo_y_telefono``` → correo en minúsculas y teléfono en E.164.
- ```test_rechaza_campo_no_editable``` (parametrizada: ```password```, ```rol```, ```estado```, ```debe_cambiar_password```, ```token_version```) → 400 y el usuario no cambia.
- ```test_put_no_esta_permitido``` → 405.
- ```test_puede_reenviar_su_propio_correo``` → no cuenta al propio usuario como duplicado.
- ```test_correo_de_otro_rechazado_sin_importar_mayusculas``` → 400 en ```correo```.
- ```test_telefono_de_otro_rechazado``` → 400 en ```telefono```.
- ```test_usuario_inexistente_responde_404```.
- ```test_sin_token_responde_401``` y ```test_no_administrador_recibe_403```.

Las pruebas funcionales de HU-17 (edición correcta y duplicado) las completa st-151 (LÓPEZ RIVAS ESTEFANÍA).