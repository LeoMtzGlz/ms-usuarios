# HU-17 — Editar los datos de un usuario

## ST-151. Pruebas

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Pruebas de HU-17: edición correcta y duplicado rechazado. Se revisaron las pruebas de st-149 y st-150 (`usuarios/tests/test_edicion_usuario.py`) contra los criterios de HU-17 y se agregaron, en un archivo aparte, los casos que faltaban. No se modificó código de la aplicación ni el archivo de pruebas de st-149 y st-150.

Depende de st-149 (endpoint de edición) y st-150 (bitácora), ya integradas en `development`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_pruebas_hu17.py` | Nuevo: 13 pruebas |

### 3. Pruebas agregadas

```bash
docker compose run --rm api pytest usuarios/tests/test_pruebas_hu17.py -v
```

**Edición correcta**

| Prueba | Qué verifica |
|---|---|
| `test_inicia_sesion_con_el_correo_nuevo_y_no_con_el_anterior` | Tras cambiar el correo, el login funciona con el nuevo y responde 401 con el anterior |
| `test_inicia_sesion_con_el_telefono_nuevo` | Tras cambiar el teléfono, el login funciona con el nuevo |
| `test_la_respuesta_trae_los_datos_editados` | La respuesta incluye `id`, `nombre`, `apellidos`, `correo` y `telefono` ya normalizados |
| `test_no_cambia_rol_ni_estado` | Editar los datos no altera el rol ni el estado |
| `test_puede_reenviar_su_propio_telefono_en_otro_formato` | Su propio teléfono en formato local no cuenta como duplicado |

**Duplicado rechazado**

| Prueba | Qué verifica |
|---|---|
| `test_correo_duplicado_usa_el_mensaje_del_catalogo` | 400 `datos_invalidos` con `CORREO_REGISTRADO` en `campos.correo` |
| `test_telefono_duplicado_usa_el_mensaje_del_catalogo` | 400 con `TELEFONO_REGISTRADO` en `campos.telefono` |
| `test_telefono_de_otro_en_formato_local_se_rechaza` | El teléfono se normaliza antes de buscar duplicados |
| `test_correo_y_telefono_duplicados_se_reportan_juntos` | Los dos errores llegan en la misma respuesta |
| `test_correo_de_una_cuenta_no_activa_tambien_se_rechaza` (2 casos) | El correo de una cuenta inactiva o pendiente tampoco se puede usar |
| `test_con_un_duplicado_no_se_guarda_ningun_cambio` | Si un campo es duplicado, tampoco se guardan los demás |
| `test_el_otro_usuario_no_se_modifica` | La cuenta dueña del correo o teléfono queda intacta |

### 4. Matriz de criterios

| Criterio de HU-17 | Pruebas |
|---|---|
| CA1. `PATCH /api/v1/usuarios/{id}/` edita nombre, apellidos, correo y teléfono | `test_edita_nombre_apellidos_correo_y_telefono`, `test_edicion_parcial_cambia_solo_lo_enviado`, `test_normaliza_correo_y_telefono` (st-149); `test_inicia_sesion_con_el_correo_nuevo_y_no_con_el_anterior`, `test_inicia_sesion_con_el_telefono_nuevo`, `test_la_respuesta_trae_los_datos_editados` (st-151) |
| CA2. No permite cambiar la contraseña ni el rol por aquí | `test_rechaza_campo_no_editable`, `test_put_no_esta_permitido` (st-149); `test_no_cambia_rol_ni_estado` (st-151) |
| CA3. Valida duplicados sin contar al propio usuario | `test_puede_reenviar_su_propio_correo`, `test_correo_de_otro_rechazado_sin_importar_mayusculas`, `test_telefono_de_otro_rechazado` (st-149); las 8 de "Duplicado rechazado" y `test_puede_reenviar_su_propio_telefono_en_otro_formato` (st-151) |
| CA4. Registra qué campos cambiaron y quién lo hizo | `test_bitacora_registra_quien_edito_y_que_campos`, `test_bitacora_no_guarda_los_valores`, `test_sin_cambios_no_registra_evento`, `test_edicion_rechazada_no_registra_evento` (st-150) |

### 5. Resultado

13 pruebas nuevas en verde. Con las de st-149 y st-150, los cuatro criterios de HU-17 quedan cubiertos.

**ST-151 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).
