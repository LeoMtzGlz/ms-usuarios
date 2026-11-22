# HU-35 — Asignar una zona a un usuario operativo

## ST-228. Pruebas de asignación de zona

**Estado:** Completada

**Responsable:** Alondra Alejandra López Medellin (22420450)

### 1. Descripción

Se realizaron pruebas automatizadas para verificar el funcionamiento de la asignación de zonas a los usuarios operativos y la incorporación del identificador de la zona dentro del token JWT.

El objetivo de esta subtarea es comprobar que la implementación realizada en ST-227 funcione correctamente, validando tanto la asignación de zonas como el comportamiento ante zonas inactivas y la generación de tokens.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/tests/test_zonas.py` | Se incorporaron tres pruebas automatizadas para verificar la asignación de zonas, el rechazo de zonas inactivas y la inclusión del identificador de zona en el JWT. |

### 3. Pruebas implementadas

Se desarrollaron las siguientes pruebas:

**Prueba 1: `test_asignar_zona_a_usuario_operativo`**

Verifica que se pueda crear un usuario operativo con una zona asignada mediante `AltaUsuarioSerializer`.

Se comprueba:

- Que el serializador acepte una zona activa.
- Que el usuario se cree correctamente.
- Que la zona quede relacionada con el usuario.
- Que el rol asignado sea `OPERATIVO`.
- Que el estado del usuario sea `ACTIVO`.

**Prueba 2: `test_no_permitir_asignar_zona_inactiva`**

Verifica que el sistema no permita asignar una zona inactiva a un usuario operativo.

Se comprueba que el serializador rechace los datos y genere un error de validación en el campo `zona`.

**Prueba 3: `test_token_incluye_identificador_de_zona`**

Verifica que el token JWT generado para un usuario operativo incluya el identificador de la zona asignada mediante el claim `zona_id`.

Se comprueba que el valor contenido en el token coincida con el identificador de la zona relacionada con el usuario.

### 4. Ejecución de pruebas específicas

Se ejecutó el siguiente comando:

```bash
pytest usuarios/tests/test_zonas.py -v
```

**Resultado obtenido:**

```text
collected 3 items

usuarios/tests/test_zonas.py::test_asignar_zona_a_usuario_operativo PASSED
usuarios/tests/test_zonas.py::test_no_permitir_asignar_zona_inactiva PASSED
usuarios/tests/test_zonas.py::test_token_incluye_identificador_de_zona PASSED

3 passed in 2.32s
```

Las tres pruebas finalizaron satisfactoriamente.

### 5. Ejecución de pruebas completas

Posteriormente se ejecutó la suite completa del proyecto mediante:

```bash
pytest
```

**Resultado obtenido:**

```text
collected 334 items

comun/tests/              PASSED
usuarios/tests/           PASSED
notificaciones/tests/     PASSED

334 passed in 83.17s (0:01:23)
```

La ejecución completa finalizó sin errores.

También se comprobó que las tres pruebas de zonas se ejecutaran correctamente dentro de la suite general.

### 6. Resultado final

Las pruebas automatizadas de la asignación de zonas finalizaron satisfactoriamente.

Se verificó que:

- Un usuario operativo puede tener una zona asignada.
- No se permite asignar una zona inactiva.
- El token JWT contiene el identificador de la zona mediante el claim `zona_id`.
- Las tres pruebas específicas finalizaron correctamente.
- La suite completa del proyecto finalizó sin pruebas fallidas.

**Resultado:** 3 pruebas específicas aprobadas y 334 pruebas de la suite completa aprobadas.

### 7. Dependencias y coordinación

Esta subtarea depende de la implementación realizada en ST-227, correspondiente a la relación entre usuarios operativos y zonas, así como la incorporación de la zona al token JWT.

**Subtarea anterior:** ST-227 — Agregar la zona al usuario operativo y al token.

**Responsable de la subtarea anterior:** Alondra Alejandra López Medellin (22420450).

**Responsable de revisión y continuación:** Daniel Orlando Ceja Olloqui.

La integración de ambas subtareas debe realizarse en orden, incorporando primero ST-227 y posteriormente ST-228.

**ST-228 finalizada.**

**Responsable de la actividad:** Alondra Alejandra López Medellin (22420450).