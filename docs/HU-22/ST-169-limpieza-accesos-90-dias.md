# HU-22 / ST-169 · Borrar en el worker los registros de acceso de más de 90 días

**Subtarea:** ID 169 · [Backend] Limpieza de registros de acceso de más de 90 días en el worker
**Historia:** HU-22 · Ver mi historial de accesos
**Responsable:** Isamar Chávez Díaz (chamar29) · **Revisa:** Isis Vázquez (isis0015)
**Rama:** `t-22/st-169` · **Depende de:** ST-167 (modelo `RegistroAcceso`, ya en development)
**Estado:** En revisión

## Descripción

Tercer criterio de HU-22: **los registros de más de 90 días se borran**. La limpieza la hace el
worker que ya existe (`procesar_notificaciones`, T-10/ST-51), pero como el worker da una vuelta
cada 5 segundos, la limpieza solo corre **una vez cada 24 horas**. Se siguió la recomendación
§3.5 del documento de investigación de la ST-170 (Isis).

## Qué cambió

| Archivo | Cambio |
| --- | --- |
| `usuarios/models.py` | Modelo `ControlLimpieza` (bloque `# t-22/st-169`): guarda cuándo fue la última limpieza |
| `usuarios/migrations/0009_controllimpieza.py` | Generada con `makemigrations` |
| `usuarios/limpieza.py` | `limpiar_accesos_viejos()` y `limpiar_si_toca()` |
| `usuarios/management/commands/limpiar_accesos.py` | Comando para limpiar a mano |
| `notificaciones/management/commands/procesar_notificaciones.py` | El worker llama a `limpiar_si_toca()` en cada vuelta (líneas `# t-22/st-169`) |
| `usuarios/tests/test_limpieza_accesos.py` | 15 pruebas (casos P21–P26 de la ST-170) |

## Cómo funciona

1. **`limpiar_accesos_viejos(dias=90)`** borra los `RegistroAcceso` con `fecha` anterior a
   `ahora - 90 días`, **por lotes de 1000** para no bloquear la tabla. Devuelve cuántos borró y
   lo escribe en el log (`svc.usuarios`).
2. **`limpiar_si_toca()`** la llama el worker cada 5 s. Busca la fila `ControlLimpieza` con
   nombre `limpiar_accesos`:
   - si la última limpieza fue hace **menos de 24 h**, no hace nada;
   - si ya pasaron 24 h (o nunca se ha hecho), limpia y guarda la hora.
3. **Varios workers:** la fila se bloquea con `select_for_update(skip_locked=True)`. El worker
   que la bloquea limpia; los demás se la saltan y en su siguiente vuelta ya no les toca.
4. Si la limpieza falla, el worker **solo lo anota en el log y sigue enviando notificaciones**.

### ¿Qué pasa con un registro de exactamente 90 días?

**Se queda.** Se borra lo que tiene **más** de 90 días (`fecha < límite`). El de 91 sí se borra.

## Cómo probarlo

```powershell
$env:SECRET_KEY = "clave-de-prueba"
$env:DATABASE_URL = "sqlite:///prueba.db"
python -m pytest usuarios/tests/test_limpieza_accesos.py -v
python manage.py migrate
python manage.py limpiar_accesos            # "N registros de acceso borrados (más de 90 días)"
python manage.py limpiar_accesos --dias 30
Remove-Item prueba.db
```

## Pruebas

| # | Prueba | Resultado |
| --- | --- | --- |
| P21 | 89 y 91 días: solo se borra el de 91 | ✅ |
| P21 | 90 días exactos: se queda | ✅ |
| P22 | Devuelve cuántos borró (2, y luego 0) | ✅ |
| — | Borra por lotes (lote de 2 con 7 viejos) | ✅ |
| — | Borra de todos los usuarios | ✅ |
| — | `dias=0` da error | ✅ |
| P23 | Comando sin parámetro usa 90 | ✅ |
| P23 | Comando `--dias 30` respeta el parámetro | ✅ |
| P23 | Comando `--dias 0` da error | ✅ |
| P24 | Dos veces el mismo día: solo limpia la primera | ✅ |
| P25 | Pasadas 24 h vuelve a limpiar | ✅ |
| — | Guarda la hora de la última limpieza | ✅ |
| P26 | No toca usuarios ni notificaciones | ✅ |
| — | El worker (`procesar_notificaciones --una-vez`) limpia | ✅ |
| — | Si la limpieza falla, el worker sigue | ✅ |

Resultado: `15 passed`.

## Checklist

- [x] `python -m ruff check .` sin errores
- [x] `python manage.py makemigrations --check --dry-run` → No changes detected
- [x] `python -m pytest` (las únicas fallas son las de PostgreSQL que también fallan en development con SQLite)
- [x] Sin `.env`, llaves ni `prueba.db` en el commit