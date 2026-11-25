# HU-18 — Desactivar o reactivar una cuenta

## ST-153. Crear los endpoints de desactivar y reactivar

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se crearon `POST /api/v1/usuarios/{id}/desactivar/` y `POST /api/v1/usuarios/{id}/reactivar/`, solo para administradores. Desactivar cambia el estado a inactivo y cierra todas las sesiones de la cuenta; reactivar la vuelve a activo. El registro nunca se borra y el cambio queda en la bitácora.

Depende de st-149 y st-150 (ruta `/api/v1/usuarios/{id}/`) y de `Usuario.cambiar_estado()` (T-02), ya integrados en `development`.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/views_admin.py` | Una importación y, al final, `DesactivarUsuarioView` y `ReactivarUsuarioView`, marcadas con `# t-18/st-153` |
| `usuarios/urls_admin.py` | Una importación y dos rutas, marcadas con `# t-18/st-153` |
| `usuarios/tests/test_desactivar_reactivar.py` | Nuevo: 20 pruebas |

No se modificó ningún modelo ni se creó ninguna migración.

### 3. Uso

```http
POST /api/v1/usuarios/{id}/desactivar/
POST /api/v1/usuarios/{id}/reactivar/
Authorization: Bearer <token de administrador>
```

Respuesta `200`:

```json
{"id": "6f1c…", "estado": "inactivo"}
```

| Caso | Respuesta |
|---|---|
| Sin token | `401 no_autenticado` |
| No es administrador | `403 sin_permiso` |
| El usuario no existe | `404 no_encontrado` |
| El administrador intenta desactivarse a sí mismo | `400 datos_invalidos`: "No puedes desactivar tu propia cuenta." |
| Reactivar una cuenta pendiente | `400 datos_invalidos`: se activa con su código de verificación, no se reactiva |
| Desactivar una cuenta ya inactiva, o reactivar una ya activa | `200` sin repetir el cambio ni el evento |
| Otro método distinto de `POST` | `405 metodo_no_permitido` |

### 4. Cómo funciona

- El cambio lo hace `Usuario.cambiar_estado()`, el único lugar del proyecto que modifica el estado:
  - al desactivar pone `is_active=False` e incrementa `token_version`, así que los refresh ya emitidos dejan de servir (HU-18, criterio 2);
  - registra el evento `estado_cambiado` con el estado anterior, el nuevo y el administrador (`por`).
- Las vistas usan `permisos_por_defecto_mas(EsAdministrador)` (st-122) y `get_object()`, que responde 404 si el usuario no existe.
- Se reutiliza el código `datos_invalidos` del catálogo; no se agregaron códigos nuevos a `comun/errores.py`.

### 5. Pruebas

```bash
docker compose run --rm api pytest usuarios/tests/test_desactivar_reactivar.py -v
```

| Prueba | Criterio de HU-18 |
|---|---|
| `test_cambia_el_estado_a_inactivo`, `test_cambia_el_estado_a_activo` | CA1 |
| `test_cierra_sus_sesiones` | CA2 |
| `test_nunca_borra_el_registro` | CA3 |
| `test_el_admin_no_puede_desactivarse_a_si_mismo` | CA4 |
| `test_registra_quien_lo_desactivo`, `test_registra_quien_la_reactivo` | Bitácora: evento `estado_cambiado` con el administrador en `por` |
| `test_desactivar_dos_veces_no_repite_el_cambio`, `test_reactivar_una_cuenta_activa_no_cambia_nada` | Peticiones repetidas |
| `test_una_cuenta_pendiente_no_se_reactiva` | Una cuenta pendiente no se salta la verificación |
| `test_sin_token_responde_401`, `test_un_no_administrador_recibe_403`, `test_usuario_inexistente_responde_404`, `test_solo_acepta_post` | Permisos y rutas |

Las pruebas de que una cuenta inactiva no inicia sesión, que su refresh no renueva y que la reactivada vuelve a entrar son de st-154.

### 6. Resultado

Los dos endpoints quedaron disponibles, con 20 pruebas en verde.

**ST-153 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).