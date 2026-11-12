# HU-28 · Recibir un aviso si alguien entra desde un dispositivo nuevo

## Objetivo
Detectar cuando un usuario inicia sesión desde un navegador o sistema operativo que no ha usado en los últimos 90 días y encolar un correo de aviso.

## Cambios técnicos realizados
- **Dependencia agregada:** `user-agents` en `requirements.txt` para parsear el User-Agent.
- **Lógica:** En el serializer de login, se compara el User-Agent actual con el historial de `RegistroAcceso` de los últimos 90 días.
- **Función de notificación:** Se utiliza `notificar()` de la app `notificaciones` con la plantilla `'dispositivo_nuevo'`.

## Reglas de negocio
- Si es el primer inicio de sesión del usuario, **no** se envía el correo.
- Si el dispositivo ya existe en los últimos 90 días, **no** se envía el correo.
- Si es un dispositivo nuevo, se encola el aviso con la fecha, dispositivo e IP.

## Endpoints afectados
- `POST /api/v1/auth/login/` (La lógica ocurre internamente tras un login exitoso). 

Nota de entorno: Al agregar la dependencia user-agents, se requiere reconstruir el contenedor con docker compose up -d --build para que los cambios surtan efecto en el entorno de desarrollo.