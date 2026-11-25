# HU-11 — Gestión de contraseñas

## ST-114. Pruebas de emisión de tokens nuevos para el dispositivo actual

**Estado:** Completada  
**Responsable:** Alondra Alejandra López Medellin  
**Revisa:** Isamar Chávez

### 1. Descripción

Se realizaron pruebas automatizadas para verificar la correcta emisión de nuevos tokens JWT después de que un usuario autenticado cambia su contraseña.

El objetivo es comprobar que el usuario pueda continuar utilizando su sesión en el dispositivo actual, que los nuevos tokens contengan los claims personalizados correspondientes y que las operaciones inválidas sean rechazadas correctamente.

También se verificó que el cambio de contraseña invalide la renovación de las sesiones anteriores, incluyendo aquellas iniciadas desde otros dispositivos.

### 2. Implementación

Se creó el archivo `usuarios/tests/test_cambiar_password_api.py`, donde se implementaron ocho pruebas automatizadas para verificar el comportamiento del endpoint `CambiarPasswordView`.

Las pruebas cubren los siguientes escenarios:

- Emisión de nuevos tokens `access` y `refresh` después de cambiar correctamente la contraseña.
- Conservación de los claims personalizados en ambos tokens.
- Incremento de `token_version` y actualización de `debe_cambiar_password`.
- Acceso correcto a un endpoint protegido utilizando el nuevo token `access`.
- Rechazo del refresh anterior y aceptación del refresh nuevo.
- Rechazo de la renovación de otra sesión iniciada desde un dispositivo diferente después del cambio de contraseña.
- Rechazo del cambio de contraseña cuando la contraseña actual es incorrecta.
- Rechazo de solicitudes sin autenticación.
- Rechazo de contraseñas nuevas que no cumplen la política de seguridad.
- Rechazo de una contraseña nueva igual a la contraseña actual, sin modificar `token_version` ni emitir tokens.

### 3. Claims verificados

Se comprobó que los nuevos tokens `access` y `refresh` contienen los siguientes claims:

- `user_id`
- `rol`
- `email_verificado`
- `token_version`
- `debe_cambiar_password`
- `zona_id`

También se verificó que `token_version` se incremente correctamente después del cambio de contraseña y que `debe_cambiar_password` quede establecido en `false`.

### 4. Resultados de las pruebas

Se ejecutaron las pruebas mediante el siguiente comando:

```powershell
pytest usuarios/tests/test_cambiar_password_api.py -v
```

**Resultado esperado después de incorporar los dos casos adicionales:**

```text
============================== test session starts ==============================
collected 8 items

test_emite_tokens_nuevos_con_claims_actualizados PASSED
test_el_nuevo_access_permite_acceder_a_endpoint_protegido PASSED
test_rechaza_refresh_anterior_y_acepta_refresh_nuevo PASSED
test_otra_sesion_no_puede_renovar_despues_del_cambio_password PASSED
test_rechaza_cambio_con_contrasena_actual_incorrecta PASSED
test_rechaza_contrasena_nueva_igual_a_la_actual PASSED
test_rechaza_solicitud_sin_autenticacion PASSED
test_rechaza_contrasena_nueva_que_no_cumple_la_politica PASSED

============================== 8 passed ==============================
```

**Resultado:** 8 pruebas aprobadas, 0 fallidas.

### 5. Consideraciones

- Las pruebas se realizaron sobre el endpoint existente `POST /api/v1/auth/cambiar-password/`.
- Se reutilizaron las fixtures existentes del proyecto para evitar duplicación de código.
- Se utilizó `APIClient` para simular sesiones independientes desde dos dispositivos.
- Se comprobó que el cambio de contraseña incrementa `token_version` y provoca que los refresh anteriores sean rechazados.
- Se verificó que el nuevo refresh permite realizar una renovación correcta de la sesión.
- Se comprobó que una sesión iniciada desde otro dispositivo ya no puede renovar sus tokens después del cambio de contraseña.
- Se verificó que intentar establecer la misma contraseña actual devuelve un error `400`, conserva la contraseña original y no modifica `token_version`.
- Se comprobó que las solicitudes inválidas no generan nuevos tokens.
- La invalidación de los refresh anteriores se comprueba mediante la validación de versión implementada en ST-90. Esto no implica que todos los access anteriores sean rechazados automáticamente.

### 6. Dependencias

- ST-112: Endpoint para cambiar contraseña.
- ST-113: Emisión de tokens nuevos para el dispositivo actual.
- ST-117: Método `Usuario.cambiar_password()`.
- ST-83: Claims personalizados de JWT.
- ST-90: Renovación y validación de tokens JWT.

**ST-114 finalizada.**

**Responsable de la actividad:** Alondra Alejandra López Medellin.