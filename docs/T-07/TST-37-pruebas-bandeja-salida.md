# T-07 — Crear la bandeja de salida de notificaciones en PostgreSQL

## ST-37. Pruebas de la bandeja de salida

**Estado:** Completada

**Responsable:** Alondra Alejandra López Medellin (22420450)

### 1. Descripción

Se realizaron pruebas automatizadas para verificar el funcionamiento de la bandeja de salida de notificaciones en PostgreSQL.

El objetivo principal de esta subtarea es comprobar que una notificación creada dentro de una transacción que posteriormente se revierte no permanezca almacenada en la base de datos.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/tests/test_services.py` | Se agregó la prueba `test_notificar_no_guarda_si_transaccion_se_revierte`. |
| `docs/T-07/ST-37-pruebas-bandeja-salida.md` | Se documentaron las pruebas realizadas y sus resultados. |

### 3. Prueba implementada

**Prueba:** `test_notificar_no_guarda_si_transaccion_se_revierte`

Se implementó una prueba utilizando `transaction.atomic()` de Django para simular una transacción que termina en una reversión (*rollback*).

El procedimiento realizado fue:

1. Crear un usuario de prueba.
2. Verificar que inicialmente no tenga notificaciones registradas.
3. Iniciar una transacción utilizando `transaction.atomic()`.
4. Crear una notificación mediante la función `notificar()`.
5. Comprobar que la notificación existe dentro de la transacción.
6. Provocar intencionalmente un `RuntimeError` para forzar el rollback.
7. Verificar que la notificación ya no exista en la base de datos después de revertirse la transacción.

**Resultado esperado:** La notificación no debe permanecer guardada después del rollback.

**Resultado obtenido:** La prueba confirmó que la notificación se elimina de la transacción revertida y que el conteo final es cero.

### 4. Ejecución de pruebas

Se ejecutó primero la prueba individual:

```bash
python -m pytest notificaciones/tests/test_services.py::test_notificar_no_guarda_si_transaccion_se_revierte -v
```

**Resultado:**

```text
1 passed in 6.51s
```

Posteriormente, se ejecutaron todas las pruebas de la aplicación de notificaciones:

```bash
pytest notificaciones/tests/ -v
```

**Resultado:**

```text
5 passed in 5.39s
```

### 5. Resultado final

La prueba individual y el conjunto de pruebas de notificaciones finalizaron correctamente.

Se verificó que:

- La notificación se crea correctamente dentro de una transacción.
- La notificación existe mientras la transacción permanece activa.
- Cuando la transacción se revierte, la notificación no permanece guardada.
- Las pruebas existentes del modelo y del servicio continúan funcionando correctamente.

**Resultado:** 5 pruebas aprobadas, 0 fallidas.

### 6. Dependencias y coordinación

Esta subtarea depende de la implementación del modelo `Notificacion` y de la función `notificar()` correspondientes a T-07.

Se utilizó la implementación realizada previamente por Katia Paola Victoria Escalera (22420438).

La prueba se desarrolló sobre dicha implementación, sin modificar el modelo ni el servicio de notificaciones.

**ST-37 finalizada.**

**Responsable de la actividad:** alondraLopez.