# HU-15 — Dar de alta a un usuario operativo

## ST-143 : Pruebas

**Estado:** Terminada. En revisión (PR ```#122```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Pruebas de HU-15: alta correcta, duplicado, no-admin 403 y que la contraseña no aparezca en ninguna otra respuesta. Se revisaron las pruebas que ya traen st-140 (```usuarios/tests/test_alta_usuario.py```), st-141 (```usuarios/tests/test_contrasenas.py```) y st-142 (```usuarios/tests/test_alta_usuario_aviso.py```) contra los cinco criterios, y se agregaron solo las que faltaban: el recorrido completo de la cuenta creada y la búsqueda de la contraseña en las demás respuestas de la API.

### Resultado:
```usuarios/tests/test_alta_operativo_criterios.py``` (6 passed: 5 pruebas, una parametrizada con dos endpoints)
- ```test_la_contrasena_no_aparece_en_el_listado``` → después del alta, la cuenta nueva **sí aparece** en ```GET /api/v1/usuarios/``` y en la búsqueda (```?search=```), y ninguna de las dos respuestas contiene la contraseña temporal (HU-16).
- ```test_la_contrasena_no_aparece_al_editar_la_cuenta``` → el ```PATCH /api/v1/usuarios/{id}/``` (HU-17) responde 200 con el nombre actualizado (```Luis Alberto```) y sin la contraseña temporal.
- ```test_el_operativo_entra_con_la_contrasena_temporal``` → con la contraseña devuelta por el alta, ```POST /api/v1/auth/login/``` responde 200 y el token lleva ```rol = operativo``` y ```debe_cambiar_password = True```.
- ```test_con_la_contrasena_temporal_un_endpoint_con_permisos_por_defecto_responde_403``` (parametrizada) → con ese token, dos endpoints representativos de los permisos por defecto (```IsAuthenticated``` + ```ContrasenaDefinitiva```) responden 403 ```debe_cambiar_password``` (HU-12): ```GET /api/v1/auth/accesos/``` y ```POST /api/v1/auth/2fa/activar/```. No se recorren todos los endpoints de la API: los que declaran sus propios permisos (por ejemplo, ```cambiar-password```) no aplican esta regla.
- ```test_al_cambiar_la_contrasena_temporal_ya_puede_trabajar``` → tras ```POST /api/v1/auth/cambiar-password/``` (HU-11), el nuevo token lleva ```debe_cambiar_password = False``` y ```/api/v1/auth/accesos/``` responde 200.

Usa ```helpers_admin.py``` (st-149) para la sesión del administrador y la zona obligatoria del alta (HU-35), igual que ```test_alta_usuario_aviso.py```.

### Matriz de criterios:
| Criterio de HU-15 | Pruebas |
|---|---|
| CA1. ```POST /api/v1/usuarios/``` (solo admin) con nombre, apellidos, correo y teléfono | ```test_alta_correcta_responde_201_con_los_datos_y_la_contrasena```, ```test_faltan_campos_obligatorios```, ```test_sin_token_responde_401```, ```test_un_no_administrador_recibe_403``` (cliente y operativo), ```test_un_administrador_con_contrasena_temporal_recibe_403```, ```test_solo_acepta_post``` (st-140) |
| CA2. Rechaza correo o teléfono duplicados | ```test_correo_duplicado_responde_400```, ```test_correo_duplicado_sin_importar_mayusculas```, ```test_telefono_duplicado_responde_400```, ```test_un_intento_fallido_no_crea_cuentas```, ```test_alta_simultanea_con_el_mismo_correo_responde_400``` (st-140) |
| CA3. Contraseña temporal de 12 caracteres, devuelta una sola vez | ```test_alta_correcta_responde_201_con_los_datos_y_la_contrasena```, ```test_la_contrasena_devuelta_es_la_que_se_guardo_y_solo_se_guarda_su_hash```, ```test_cada_alta_genera_una_contrasena_distinta```, ```test_la_respuesta_no_se_guarda_en_cache```, ```test_la_contrasena_no_aparece_en_la_bitacora``` (st-140); ```test_tiene_doce_caracteres_por_defecto```, ```test_cumple_la_politica_de_contrasenas``` (st-141); ```test_la_contrasena_no_aparece_en_el_listado```, ```test_la_contrasena_no_aparece_al_editar_la_cuenta``` (st-143) |
| CA4. Activa, rol Operativo y ```debe_cambiar_password=True``` | ```test_la_cuenta_queda_activa_operativa_y_con_contrasena_temporal```, ```test_ignora_rol_estado_y_permisos_enviados_por_el_cliente``` (st-140); ```test_el_operativo_entra_con_la_contrasena_temporal```, ```test_con_la_contrasena_temporal_un_endpoint_con_permisos_por_defecto_responde_403```, ```test_al_cambiar_la_contrasena_temporal_ya_puede_trabajar``` (st-143) |
| CA5. Aviso de cuenta creada por correo, sin la contraseña | ```test_el_alta_encola_un_aviso_por_correo_para_la_cuenta_creada```, ```test_la_contrasena_no_se_guarda_en_la_bandeja_de_salida```, ```test_el_correo_armado_no_lleva_la_contrasena_y_da_instrucciones```, ```test_un_alta_rechazada_no_encola_nada``` (st-142) |

### Hallazgos:
Ninguno: los cinco criterios se cumplen. No se modificó código de la aplicación ni los archivos de pruebas de st-140, st-141 y st-142.

### Cambios tras la revisión:
- La prueba del listado confirma primero que la cuenta nueva aparece en el listado y en la búsqueda, para que la comprobación de la contraseña no quede vacía.
- La prueba de edición verifica también el nombre actualizado.
- La prueba de autorización se parametrizó con dos endpoints representativos de los permisos por defecto, y el documento ya no dice que se prueban «los demás endpoints».