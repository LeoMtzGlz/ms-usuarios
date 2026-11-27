# HU-28 · Recibir un aviso si alguien entra desde un dispositivo nuevo

**Estado:** Terminado
**Responsable:** Angel Canela (l22420453)
**Descripción:** Se implementó la detección de dispositivos no reconocidos en el login. Se compara el navegador y sistema operativo del usuario contra su historial de accesos exitosos en los últimos 90 días. Si el dispositivo es nuevo, se encola una notificación por correo usando la función `notificar()`.

## Resultado
El sistema identifica si el dispositivo del usuario ha sido visto antes, evitando alertas innecesarias, y envía una alerta por correo cuando detecta un dispositivo no reconocido.

## Cobertura de Pruebas (t-28/st-198)
Se implementaron 5 pruebas unitarias en `usuarios/tests/test_dispositivo_nuevo.py` que cubren los siguientes escenarios de seguridad:
1. Un dispositivo nuevo (sin historial previo) genera una notificación.
2. Un dispositivo conocido (usado en los últimos 90 días) NO genera notificación.
3. Un dispositivo con historial mayor a 90 días se considera nuevo y SÍ notifica.
4. Un intento de inicio de sesión fallido NO marca el dispositivo como conocido.
5. El mismo navegador en diferentes sistemas operativos (Windows vs Mac) se identifica como un dispositivo nuevo.