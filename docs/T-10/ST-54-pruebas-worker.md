# T-10 — Procesar la bandeja de salida con reintentos y respaldo de canal

## ST-54. Pruebas del worker

**Estado:** En revisión

### 1. Descripción

Pruebas de flujo completo del worker: cada una corre varios ciclos de `procesar_lote()` (o del comando
`--una-vez`) con un canal falso que falla un número controlado de veces. Complementan las pruebas unitarias
de ST-51 (`test_worker.py`) y ST-52 (`test_reintentos_respaldo.py`), que miran una sola función o un solo ciclo.
Diseño aprobado en `docs/T-10/ST-52-diseno-reintentos-respaldo.md`. No se tocó código de producción.

Archivo nuevo: `notificaciones/tests/test_worker_flujo.py` (10 pruebas).

### 2. Qué cubre cada prueba

| Prueba | Qué comprueba |
|---|---|
| `test_exito_en_el_primer_ciclo` | Enviada en el primer ciclo, sin intentos, contexto vacío; el segundo ciclo no la reenvía |
| `test_falla_dos_veces_y_sale_al_tercer_ciclo` | Dos fallos la dejan pendiente con `intentos` 1 y 2; el tercer ciclo la envía y limpia el error |
| `test_whatsapp_agota_intentos_y_la_copia_sale_por_correo` | Tres fallos por WhatsApp: original `fallida`, copia por correo pendiente con el `creado_en` original; en el ciclo 4 la copia sale al `email` del usuario y queda `enviada` |
| `test_correo_agota_intentos_y_queda_fallida_sin_copia` | Correo: tras 3 fallos queda `fallida`, contexto vacío, sin copia ni más ciclos |
| `test_codigo_vencido_no_se_envia` | Código de 11 min con `minutos: 10`: `fallida`, «Código vencido: no se envió», contexto vacío, no se reintenta |
| `test_codigo_vencido_de_whatsapp_no_genera_copia` | Un código vencido de WhatsApp no se respalda por correo |
| `test_codigo_vigente_si_se_envia` | Código de 9 min con `minutos: 10`: se envía |
| `test_el_codigo_no_aparece_en_error_ni_en_el_contexto_final` | Aunque el proveedor repita el código en su error, no queda en `error` en ningún ciclo ni en el contexto final |
| `test_un_lote_mixto` | En un lote, una vencida, una que reintenta y una exitosa terminan cada una en su estado; la que reintenta no frena a las demás |
| `test_el_comando_una_vez_aplica_los_reintentos` | `procesar_notificaciones --una-vez` tres veces: pendiente (1), pendiente (2), `fallida` (3) |

### 3. Cómo correrlas

```bash
docker compose run --rm api pytest notificaciones/tests/test_worker_flujo.py -v
```

### 4. Lo que NO cubre

- **WhatsApp real** (Meta): se usa un canal falso; el envío real y sus errores son de T-09.
- **El límite diario por canal** de ST-57 (`antes_de_enviar()` hoy siempre deja pasar).
- Esperas entre reintentos: no hay backoff, se reintenta en el siguiente ciclo de 5 s.

### 5. Resultado

Las 10 pruebas nuevas pasan sin cambios en `worker.py` (no revelaron defectos). Sobre PostgreSQL 16 y Python 3.12:
`ruff check .` sin hallazgos, `makemigrations --check --dry-run` sin cambios y `pytest` completo con
421 pasadas y 1 xfail (preexistente).
