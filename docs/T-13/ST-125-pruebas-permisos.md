# T-13 — Definir los roles y las clases de permiso

## ST-125. Pruebas de permisos

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se escribieron las pruebas que verifican que cada clase de permiso de ST-122 permite y niega a los roles correctos. El token se simula con un diccionario para que las pruebas no dependan de las llaves RS256.

### 2. Archivo

`comun/tests/test_permisos.py` (21 pruebas).

### 3. Casos probados

| Caso | Criterio |
|---|---|
| Matriz rol × clase (9 combinaciones): 200 al rol correcto y 403 `sin_permiso` a los demás | T-13 criterio 2 / HU-13 criterio 1 |
| Sin token responde 401 `no_autenticado` en las 4 clases | HU-13 criterio 1 |
| Un cliente no accede a los datos de otro cliente | HU-13 criterio 2 |
| El dueño accede a lo suyo y el administrador a todo | T-13 criterio 2 |
| Dueño por campo `usuario_id`; un objeto sin dueño se niega | T-13 criterio 2 |
| Token sin claim `rol` se niega; el rol se toma del token | Diseño de E06 |

### 4. Cómo ejecutarlas

```bash
docker compose run --rm api pytest comun/tests/test_permisos.py -v
```

### 5. Resultado

21 pruebas en verde (`21 passed`). Se integraron junto con ST-122 en el PR #15.

**ST-125 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).
