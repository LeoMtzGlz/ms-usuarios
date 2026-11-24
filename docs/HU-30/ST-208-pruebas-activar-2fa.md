# HU-30 — Activar la verificación en dos pasos (2FA)

## ST-208 : Pruebas

**Estado:** Terminada. En revisión (PR ```t-30/st-208: Pruebas de HU-30```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Pruebas de HU-30: activación y código incorrecto. Se revisaron las pruebas de st-206 (```usuarios/tests/test_2fa_endpoints.py```) y se agregaron las que faltaban para el criterio de los códigos de respaldo (st-207).

### Resultado: 
```usuarios/tests/test_activar_2fa.py``` (5 passed). Usa el mismo esquema que st-206: ```UsuarioFactory```, ```force_authenticate``` y una clave Fernet temporal en ```settings.CLAVE_CIFRADO_2FA```.
- ```test_confirmar_entrega_10_codigos_de_respaldo``` → la respuesta trae 10 códigos distintos en ```codigos_respaldo```.
- ```test_los_codigos_se_guardan_con_hash``` → ningún código aparece en claro en ```CodigoRespaldo```.
- ```test_codigo_incorrecto_no_genera_codigos``` → si la confirmación falla (```codigo_invalido```), no se crea ningún código.
- ```test_los_codigos_no_vuelven_a_mostrarse``` → un segundo ```activar``` responde ```dos_factores_ya_activo``` y no los incluye.
- ```test_los_codigos_no_van_a_la_bitacora``` → se registra ```2fa_activado``` en ```svc.auditoria```, pero sin los códigos.

El código incorrecto se elige con ```pyotp``` (```verify(..., valid_window=1)```), como en st-206, así que las pruebas no fallan en el cambio de ventana de 30 segundos.

### Matriz de criterios: 
| Criterio de HU-30 | Pruebas |
|---|---|
| CA1. ```POST /auth/2fa/activar/``` devuelve el QR y el secreto | ```test_activar_devuelve_secreto_uri_y_qr```, ```test_activar_exige_sesion``` (st-206) |
| CA2. Se activa solo tras confirmar un primer código | ```test_el_secreto_se_guarda_cifrado_y_sin_confirmar```, ```test_confirmar_con_codigo_correcto_activa_el_2fa```, ```test_confirmar_con_codigo_incorrecto_no_activa```, ```test_confirmar_sin_haber_activado```, ```test_confirmar_con_formato_invalido``` (st-206) |
| CA3. Entrega 10 códigos de respaldo una sola vez | ```test_confirmar_entrega_10_codigos_de_respaldo```, ```test_los_codigos_se_guardan_con_hash```, ```test_codigo_incorrecto_no_genera_codigos```, ```test_los_codigos_no_vuelven_a_mostrarse```, ```test_los_codigos_no_van_a_la_bitacora``` (st-208) |
| CA4. El secreto se guarda cifrado | ```test_el_secreto_se_guarda_cifrado_y_sin_confirmar``` (st-206), ```usuarios/tests/test_dispositivo2fa.py``` (st-205) |