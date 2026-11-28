# HU-10 — Recuperar mi contraseña

## ST-110. Pruebas de recuperación

**Estado:** Completada  
**Responsable:** Katia Paola Victoria Escalera (22420438)

### 1. Descripción
Se completó la batería de pruebas unitarias para el flujo de recuperación de contraseña, cubriendo escenarios positivos y negativos.

### 2. Pruebas agregadas
- `test_restablecer_codigo_incorrecto`: Verifica el rechazo de códigos inválidos.
- `test_restablecer_codigo_vencido`: Verifica el rechazo si el código ya expiró.
- `test_restablecer_passwords_no_coinciden`: Valida que la contraseña y su confirmación sean idénticas.

### 3. Resultado
Todas las pruebas pasan en verde. El flujo está blindado contra errores de usuario y ataques básicos.