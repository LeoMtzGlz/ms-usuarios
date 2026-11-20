# T-08 — Configurar el canal de correo con un SMTP gratuito

## ST-41. Crear el CanalCorreo con EmailMultiAlternatives

**Estado:** Completada

**Responsable:** Alondra Alejandra López Medellin (22420450)

### 1. Descripción

Se implementó el canal de envío de notificaciones por correo electrónico utilizando `EmailMultiAlternatives` de Django y la configuración SMTP definida en el proyecto.

El objetivo principal de esta subtarea es permitir que el sistema envíe notificaciones a los usuarios mediante correo electrónico, utilizando los parámetros de conexión configurados en las variables de entorno.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `config/settings.py` | Se configuraron los parámetros de correo electrónico para utilizar el servidor SMTP. |
| `.env` | Se incorporaron las variables de configuración SMTP, como host, puerto, TLS, usuario y contraseña. |
| `notificaciones/canales.py` | Se implementó la clase `CanalCorreo` utilizando `EmailMultiAlternatives` para enviar correos electrónicos. |
| `notificaciones/services.py` | Se actualizó la selección del canal para permitir obtener una instancia de `CanalCorreo` cuando la configuración indica el canal de correo. |
| `notificaciones/tests/test_canales.py` | Se agregaron pruebas automatizadas para verificar el envío de correos y la selección del canal. |

### 3. Implementación realizada

**Clase implementada:** `CanalCorreo`

Se creó la clase `CanalCorreo`, que implementa la interfaz `Canal` definida previamente.

Para realizar el envío se utilizó `EmailMultiAlternatives`, proporcionando los siguientes datos:

- Destinatario del correo.
- Asunto del mensaje.
- Contenido del correo.
- Dirección de envío configurada en `DEFAULT_FROM_EMAIL`.

El envío se realiza mediante el método `send()` con `fail_silently=False`, permitiendo que los errores durante el envío sean reportados.

También se actualizó la función `obtener_canal()` para que pueda devolver una instancia de `CanalCorreo` cuando `CANAL_NOTIFICACIONES` está configurado con el valor `correo`.

### 4. Prueba manual de envío

Se realizó una prueba manual desde la consola interactiva de Django para comprobar el funcionamiento del canal de correo mediante la configuración SMTP.

**Comando ejecutado:**

```bash
python manage.py shell
```

**Código utilizado:**

```python
from notificaciones.canales import CanalCorreo

canal = CanalCorreo()

canal.enviar(
    destino="medellinalondra70@gmail.com",
    asunto="Prueba CanalCorreo",
    texto="Hola, este es un correo de prueba desde Django."
)
```

**Resultado obtenido:**

```text
2026-11-18 13:41:43,777 INFO svc.notificaciones
Correo enviado correctamente a: medellinalondra70@gmail.com
```

La ejecución finalizó sin errores y el canal registró el envío correcto del correo.

### 5. Pruebas automatizadas

Se creó el archivo `notificaciones/tests/test_canales.py` con dos pruebas:

**Prueba 1:** `test_canal_correo_envia_mensaje`

Verifica que `CanalCorreo` envíe correctamente un mensaje utilizando el backend de correo en memoria de Django.

Se comprueban los siguientes elementos:

- Que se genere un correo.
- Que el asunto sea correcto.
- Que el contenido del mensaje coincida con el esperado.
- Que la dirección del remitente sea la configurada.
- Que el destinatario sea el indicado.

**Prueba 2:** `test_obtener_canal_devuelve_canal_correo`

Verifica que la función `obtener_canal()` devuelva una instancia de `CanalCorreo` cuando la configuración del sistema establece `CANAL_NOTIFICACIONES="correo"`.

**Comando ejecutado:**

```bash
python -m pytest notificaciones/tests/test_canales.py -v
```

**Resultado obtenido:**

```text
collected 2 items

notificaciones/tests/test_canales.py::test_canal_correo_envia_mensaje PASSED
notificaciones/tests/test_canales.py::test_obtener_canal_devuelve_canal_correo PASSED

2 passed in 4.59s
```

### 6. Resultado final

La implementación del canal de correo y sus pruebas automatizadas finalizaron correctamente.

Se verificó que:

- El sistema puede utilizar la configuración SMTP definida para el correo electrónico.
- La clase `CanalCorreo` implementa el envío mediante `EmailMultiAlternatives`.
- El envío manual desde la consola de Django se ejecutó sin errores.
- La función `obtener_canal()` identifica y devuelve el canal de correo cuando corresponde.
- Las dos pruebas automatizadas finalizaron satisfactoriamente.

**Resultado:** 2 pruebas aprobadas, 0 fallidas.

### 7. Dependencias y coordinación

Esta subtarea utiliza la interfaz abstracta `Canal` y la implementación de `CanalConsola` desarrolladas previamente para el sistema de notificaciones.

Se mantuvo la estructura existente de los canales para incorporar el envío por correo sin modificar el modelo `Notificacion`.

La integración con las plantillas de correo electrónico corresponde a la subtarea encargada de desarrollar dichas plantillas.

**ST-41 finalizada.**

**Responsable de la actividad:** alondraLopez.