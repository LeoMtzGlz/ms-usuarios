# ST-175: Pruebas de eliminar cuenta

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Historia:** HU-23 · Eliminar mi cuenta
**Descripción:** Pruebas de punta a punta, por la API, de los criterios de HU-23.

## Qué cubre cada archivo de pruebas
| Archivo | Subtarea | Qué prueba |
| --- | --- | --- |
| `test_anonimizacion.py` | ST-173 | La función `anonimizar_usuario()` por separado |
| `test_eliminar_cuenta.py` | ST-174 | El contrato del endpoint: validaciones, 401/403, correo de confirmación, único administrador |
| `test_eliminar_cuenta_efectos.py` | ST-175 | Los efectos reales tras llamar al endpoint (abajo) |

## Criterios de HU-23 y su prueba
| Criterio | Pruebas en `test_eliminar_cuenta_efectos.py` |
| --- | --- |
| Nombre, correo y teléfono se anonimizan | `test_nombre_correo_y_telefono_quedan_anonimizados`, `test_conserva_id_rol_y_fechas` |
| La cuenta queda inactiva | `test_la_cuenta_queda_inactiva`, `test_la_contrasena_anterior_ya_no_sirve` |
| Los registros relacionados se conservan | `test_conserva_el_historial_de_accesos_y_la_bitacora`, `test_la_bitacora_registra_la_eliminacion_sin_datos_personales` |
| Se cierran todas las sesiones | `test_el_token_de_acceso_deja_de_servir_y_no_se_puede_eliminar_dos_veces`, `test_token_version_sube_una_sola_vez`, `test_todos_los_refresh_tokens_quedan_en_la_lista_negra`, y las dos pruebas de inicio de sesión rechazado (correo y teléfono) |
| Credenciales y avisos borrados | códigos y segundo factor, notificaciones pendientes y contenido de las enviadas, intentos de django-axes |
| Correo y teléfono quedan libres | `test_se_puede_registrar_de_nuevo_con_el_mismo_correo_y_telefono` |
| Todo o nada | `test_si_la_anonimizacion_falla_la_cuenta_queda_intacta`, `test_el_unico_administrador_conserva_todo` |

El correo de confirmación y la regla del único administrador ya se prueban en ST-174.

## Pruebas
docker compose run --rm api pytest usuarios/tests/test_eliminar_cuenta_efectos.py -v