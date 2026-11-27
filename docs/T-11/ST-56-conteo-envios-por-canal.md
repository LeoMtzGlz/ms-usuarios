# T-11 — Controlar las cuotas gratuitas de cada canal

## ST-56. Contar los envíos del día por canal en PostgreSQL

**Estado:** En revisión
**Responsable:** Maritza Santibañez (22420423)

### 1. Descripción

Función reutilizable que devuelve cuántas notificaciones se enviaron hoy por un canal. Es la base de
ST-57, que compara este conteo con el límite diario de cada canal antes de enviar
(punto de enganche `antes_de_enviar()` en `notificaciones/worker.py`). Esta subtarea solo cuenta: no
aplica límites, no cambia de canal ni pospone envíos.

```python
from notificaciones.services import contar_envios_hoy

contar_envios_hoy(CanalNotificacion.CORREO)    # -> int
contar_envios_hoy(CanalNotificacion.WHATSAPP)  # -> int
```

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/services.py` | Función nueva `contar_envios_hoy(canal)` al final del archivo. |
| `notificaciones/tests/test_conteo_envios.py` | 6 pruebas nuevas. |
| `docs/T-11/ST-56-conteo-envios-por-canal.md` | Esta documentación. |

No se tocaron modelos, migraciones, `settings.py` ni otros archivos compartidos.

### 3. Cómo cuenta

- Filtra `Notificacion` por `canal`, `estado = enviada` y fecha de envío dentro del día local.
- "Hoy" es el día en `TIME_ZONE` (`America/Mexico_City`), no el día UTC: un envío a las 23:45 de ayer
  (hora local) no cuenta aunque en UTC ya sea hoy.
- El día se filtra como rango `[00:00 de hoy, 00:00 de mañana)` en lugar de `actualizado_en__date`,
  para que PostgreSQL compare la columna directamente sin convertir la fecha de cada fila.
- Las notificaciones `pendiente` y `fallida` no cuentan.

### 4. Limitación: fecha de envío

El modelo no tiene un campo `enviado_en`, así que se usa `actualizado_en` como fecha de envío.
Hoy es correcto porque:

- `marcar_enviada()` del worker es el último `save()` que recibe una notificación enviada.
- La anonimización (`usuarios/anonimizacion.py`) usa `.update()`, que no modifica `auto_now`.

Si en el futuro algún código hace `save()` sobre una notificación ya enviada, su `actualizado_en`
cambiaría y el envío podría contarse en otro día. Si eso llega a pasar, la solución es agregar un campo
`enviado_en` (con su migración) y contar sobre él; queda fuera del alcance de ST-56.

### 5. Pruebas

| Prueba | Qué comprueba |
|---|---|
| `test_contar_envios_hoy_por_canal` | El conteo separa correo y WhatsApp |
| `test_contar_envios_hoy_excluye_pendientes_y_fallidas` | Solo cuentan las enviadas |
| `test_contar_envios_hoy_excluye_dias_anteriores` | Un envío de ayer no cuenta |
| `test_contar_envios_hoy_sin_registros` | Sin envíos devuelve 0 |
| `test_contar_envios_hoy_respeta_zona_horaria` | 23:45 de ayer (local) no cuenta; 00:15 de hoy sí |
| `test_contar_envios_hoy_excluye_desde_medianoche_siguiente` | El último instante de hoy cuenta; la medianoche de mañana no |

```bash
docker compose run --rm api pytest notificaciones/tests/test_conteo_envios.py -v
```

### 6. Resultado

Sobre PostgreSQL 16, con la rama actualizada con `development`: `ruff check .` sin hallazgos,
`makemigrations --check --dry-run` sin cambios, `migrate` correcto y `pytest` completo en verde.
