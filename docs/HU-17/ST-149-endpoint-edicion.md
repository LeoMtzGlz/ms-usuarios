# HU-17 — Editar los datos de un usuario

## ST-149 : Crear el endpoint de edición

**Estado:** Terminada. En revisión (PR ```#94```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Endpoint para que un administrador edite los datos de contacto de un usuario.
- ```PATCH /api/v1/usuarios/{id}/``` edita nombre, apellidos, correo y teléfono.
- No permite cambiar la contraseña ni el rol por aquí.
- Valida duplicados sin contar al propio usuario (```exclude(pk=...)```).

### Resultado:
- ```usuarios/serializers_admin.py```: ```EdicionUsuarioSerializer```
  - Campos editables (```CAMPOS_EDITABLES```): ```nombre```, ```apellidos```, ```correo``` y ```telefono```, los mismos nombres que el alta de HU-15. Se guardan en ```first_name```, ```last_name```, ```email``` y ```telefono``` (```source=```).
  - Lista blanca: cualquier otro campo (```password```, ```rol```, ```estado```, ```debe_cambiar_password```, ```token_version```, ```email```…) responde 400 con un mensaje por campo.
  - Correo: se normaliza a minúsculas y se rechaza si otra cuenta lo tiene, sin importar mayúsculas (```email__iexact``` + ```exclude(pk=...)```).
  - Teléfono: se normaliza a E.164 con ```normalizar_telefono()``` (```usuarios/telefono.py```) y se rechaza si otra cuenta lo tiene.
  - Mensajes de duplicado: ```CORREO_REGISTRADO``` y ```TELEFONO_REGISTRADO``` (```usuarios/serializers.py```), los mismos del alta.
  - Si dos ediciones compiten, el ```IntegrityError``` de la restricción única se convierte en 400 en ```correo``` o ```telefono```.
- ```usuarios/views_admin.py```: ```UsuarioDetalleView``` (```UpdateModelMixin``` + ```GenericAPIView```) con ```permission_classes = permisos_por_defecto_mas(EsAdministrador)```. Solo define ```patch```: ```GET```, ```POST``` y ```PUT``` sobre el detalle responden 405, y 404 si el usuario no existe. Responde 200 con ```id```, ```nombre```, ```apellidos```, ```correo```, ```telefono```, ```rol``` y ```estado``` (sin contraseña).
- ```usuarios/urls_admin.py```: ruta ```<uuid:pk>/``` hacia ```UsuarioDetalleView```. La ruta y la vista de Sergio (```UsuariosView```, alta y listado) no se modificaron.
- ```usuarios/tests/helpers_admin.py``` (nuevo): ```crear_usuario()``` y ```api_de()```, que autentica con un token real de ```CustomTokenObtainPairSerializer.get_token()```. Lo reutilizan las pruebas de HU-15, HU-17 y HU-19.

### Decisiones:
- A diferencia del alta (que ignora campos extra), la edición **rechaza** los campos no editables con 400, porque el criterio dice que no se permite cambiarlos por aquí y así el cliente sabe que no se aplicaron.
- La edición va en una vista propia (```UsuarioDetalleView```) para que ```PATCH /api/v1/usuarios/``` sin id responda 405 y el detalle no ejecute el listado ni el alta.
- No hay ```DELETE```: los usuarios no se borran (HU-18).

### Pruebas:
```usuarios/tests/test_edicion_usuario.py``` (19 passed)
- ```test_edita_nombre_apellidos_correo_y_telefono``` → los cuatro campos se guardan en el modelo y la respuesta usa ```correo```.
- ```test_edicion_parcial_cambia_solo_lo_enviado``` → un PATCH con un campo no toca los demás.
- ```test_normaliza_correo_y_telefono``` → correo en minúsculas y teléfono en E.164.
- ```test_la_respuesta_no_incluye_la_contrasena```.
- ```test_rechaza_campo_no_editable``` (parametrizada: ```password```, ```rol```, ```estado```, ```debe_cambiar_password```, ```token_version```, ```email```) → 400 y el usuario no cambia.
- ```test_put_no_esta_permitido```, ```test_get_en_el_detalle_no_esta_permitido``` y ```test_patch_sin_id_no_esta_permitido``` → 405.
- ```test_puede_reenviar_su_propio_correo``` → no cuenta al propio usuario como duplicado.
- ```test_correo_de_otro_rechazado_sin_importar_mayusculas``` → 400 en ```correo```.
- ```test_telefono_de_otro_rechazado``` → 400 en ```telefono```.
- ```test_no_admin_recibe_403```, ```test_sin_token_recibe_401``` y ```test_usuario_inexistente_responde_404```.

Las pruebas funcionales de HU-17 (edición correcta y duplicado) las completa st-151 (LÓPEZ RIVAS ESTEFANÍA).