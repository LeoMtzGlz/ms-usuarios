# HU-22 / ST-168 · Crear el endpoint de historial

**Subtarea:** ID 168 · [Backend] Crear el endpoint de historial
**Historia:** HU-22 · Ver mi historial de accesos
**Responsable:** Isamar Chávez Díaz (chamar29) · **Revisa:** Isis Vázquez (isis0015)
**Estado:** En revisión

## Descripción

`GET /api/v1/auth/accesos/` devuelve el historial de accesos de **la persona del token**: los
últimos 20 por página, del más reciente al más antiguo, con el dispositivo legible que guardó la
ST-167. Cubre el criterio de HU-22: *"GET /api/v1/auth/accesos/ muestra los últimos 20 con
dispositivo legible"*.

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `usuarios/views_accesos.py` | Serializer, paginación de 20 y `HistorialAccesosView` (archivo nuevo) |
| `usuarios/urls.py` | Ruta `accesos/` (líneas marcadas `# t-22/st-168`) |
| `usuarios/tests/test_historial_accesos_endpoint.py` | 9 pruebas |

## Respuesta

```http
GET /api/v1/auth/accesos/
Authorization: Bearer <access_token>
```

```json
{
  "count": 25,
  "next": "http://localhost:8000/api/v1/auth/accesos/?page=2",
  "previous": null,
  "results": [
    {"fecha": "2026-11-20T11:30:00-06:00", "ip": "201.141.10.5", "dispositivo": "Chrome 131 en Windows 10", "exitoso": true},
    {"fecha": "2026-11-20T11:29:12-06:00", "ip": "201.141.10.5", "dispositivo": "Mobile Safari 17 en iOS 17.1", "exitoso": false}
  ]
}
```

## Decisiones (siguiendo el plan de pruebas de Isis, ST-170 §3.6)

- **Solo mis accesos:** el queryset siempre filtra por `request.user`. Parámetros como
  `?usuario=<otro>` se ignoran.
- **20 por página, sin excepción:** paginación solo en esta vista (`PageNumberPagination`,
  `page_size = 20`); `?page_size=1000` se ignora. Orden `-fecha` con desempate por `-id`.
- **Sin datos de más:** solo `fecha`, `ip`, `dispositivo` y `exitoso`; no se expone el
  user-agent crudo ni el id del usuario.
- **Permisos por defecto:** sin token → 401 `no_autenticado`; con contraseña temporal → 403
  `debe_cambiar_password` (ST-116).

## Pruebas

| Prueba | Esperado |
| --- | --- |
| `test_sin_token_responde_401` | 401 `no_autenticado` |
| `test_solo_veo_mis_accesos` | Solo los 3 míos, ninguno de los 4 del otro |
| `test_parametro_de_otro_usuario_se_ignora` | `?usuario=<otro>` no cambia nada |
| `test_pagina_de_20_mas_recientes_primero` | 20 en la página 1, más recientes primero; la página 2 trae 5 |
| `test_no_se_pueden_pedir_mas_de_20` | `?page_size=1000` sigue dando 20 |
| `test_campos_de_la_respuesta` | Solo `fecha`, `ip`, `dispositivo`, `exitoso` |
| `test_sin_registros_devuelve_lista_vacia` | 200 con `results: []` |
| `test_con_contrasena_temporal_responde_403` | 403 `debe_cambiar_password` |
| `test_el_login_real_aparece_en_mi_historial` | Un login de la ST-81 aparece en el historial |

```powershell
docker compose run --rm api pytest usuarios/tests/test_historial_accesos_endpoint.py -v
```

Resultado: 9 pruebas en verde; `ruff` y `makemigrations --check` limpios.

## Pendiente

- **ST-169:** borrar los registros de más de 90 días desde el worker.
- **ST-170 (Isis):** pruebas de toda la historia.