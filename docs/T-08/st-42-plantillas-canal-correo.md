# T-08 — Configurar el canal de correo con un SMTP gratuito

## ST-42. [Backend] Crear las 5 plantillas de correo

**Estado:** Completada

**Responsable:** Daniel Orlando Ceja Olloqui (22420448)

### 1. Descripción

Se diseñaron e implementaron las 5 plantillas de correo electrónico del servicio `svc-usuarios` utilizando el motor de plantillas de Django, heredando de una plantilla base común (`base.html`) que incluye el pie de página institucional `"Correo automático, no respondas."`.

El objetivo principal de esta subtarea es estandarizar la estructura visual y textual de los correos enviados por el sistema, generando tanto la versión en texto plano como la versión alternativa en formato HTML (`text/html`) para su despacho multiparte mediante `CanalCorreo`.

### 2. Cambios realizados

| Archivo | Cambio |
| --- | --- |
| `notificaciones/templates/notificaciones/correo/base.html` | Se creó la plantilla base común con estructura responsiva, cabecera, bloque de contenido y pie de página obligatorio `"Correo automático, no respondas."`. |
| `notificaciones/templates/notificaciones/correo/activacion.html` | Se creó la plantilla para el envío del código de verificación y activación de cuenta. |
| `notificaciones/templates/notificaciones/correo/bienvenida.html` | Se creó la plantilla de confirmación tras la activación exitosa de la cuenta. |
| `notificaciones/templates/notificaciones/correo/recuperacion_password.html` | Se creó la plantilla para solicitudes de restablecimiento de contraseña mediante código o enlace. |
| `notificaciones/templates/notificaciones/correo/cambio_password.html` | Se creó la plantilla de notificación de seguridad tras un cambio de contraseña. |
| `notificaciones/templates/notificaciones/correo/bloqueo_cuenta.html` | Se creó la plantilla de alerta por bloqueo temporal de cuenta tras intentos fallidos. |
| `notificaciones/plantillas.py` | Se implementó el diccionario `PLANTILLAS_CORREO` y la función `renderizar_plantilla_correo()` para obtener asunto, texto plano limpio y HTML. |
| `notificaciones/canales.py` | Se actualizó `CanalCorreo.enviar()` (y la interfaz `Canal`) para aceptar el parámetro opcional `html` y adjuntarlo mediante `attach_alternative(html, "text/html")`. |
| `notificaciones/services.py` | Se incorporó `preparar_contenido_notificacion()` para resolver el contenido renderizado a partir de la plantilla y contexto de cada notificación. |
| `notificaciones/tests/test_plantillas_correo.py` | Se agregaron pruebas automatizadas para validar las 5 plantillas, el pie común, el manejo de plantillas inválidas y el envío HTML multiparte. |

### 3. Implementación realizada

**Módulo y plantillas implementadas:** `notificaciones/plantillas.py` y `notificaciones/templates/notificaciones/correo/`

Se creó la plantilla base `base.html` y las 5 plantillas específicas (`activacion`, `bienvenida`, `recuperacion_password`, `cambio_password` y `bloqueo_cuenta`), asegurando que todas incluyan el pie común `"Correo automático, no respondas."`.

Para el procesamiento de cada mensaje se implementó la función `renderizar_plantilla_correo(nombre_plantilla, contexto)`, la cual realiza las siguientes operaciones:

* Valida que la plantilla solicitada exista dentro de `PLANTILLAS_CORREO` (manteniendo compatibilidad con el alias `codigo_activacion`).
* Renderiza el documento HTML con las variables del contexto proporcionado.
* Extrae una versión en texto plano limpia eliminando etiquetas HTML y bloques `<style>`.
* Devuelve la tupla `(asunto, texto_plano, html)`.

Adicionalmente, se extendió el método `enviar()` de `CanalCorreo` con el parámetro opcional `html: str | None = None` para adjuntar la alternativa `text/html` sin alterar las llamadas previas en texto plano.

### 4. Prueba manual de renderizado

Se realizó una prueba manual desde la consola interactiva de Django para comprobar el correcto renderizado de las plantillas, la sustitución de variables de contexto y la inclusión del pie de página requerido.

**Comando ejecutado:**

```bash
python manage.py shell

```

**Código utilizado:**

```python
from notificaciones.plantillas import renderizar_plantilla_correo

asunto, texto, html = renderizar_plantilla_correo(
    "activacion",
    {"nombre": "Daniel", "codigo": "482910"}
)
print(asunto)
print(texto)

```

**Resultado obtenido:**

```text
Activa tu cuenta
Activación de Cuenta
Hola Daniel,
Gracias por registrarte. Utiliza el siguiente código para verificar y activar tu cuenta:
482910
Este código expirará en 15 minutos. Si no solicitaste este registro, ignora este mensaje.
Correo automático, no respondas.

```

La ejecución finalizó sin errores y generó correctamente el asunto, el cuerpo en texto plano y el contenido HTML con el pie común.

### 5. Pruebas automatizadas

Se creó el archivo `notificaciones/tests/test_plantillas_correo.py` con 8 casos de prueba (parametrizados) y se ejecutó junto con toda la suite de `notificaciones` y el linter `ruff`:

**Prueba 1:** `test_renderizar_5_plantillas_con_pie_comun`

Verifica de forma parametrizada las 5 plantillas (`activacion`, `bienvenida`, `recuperacion_password`, `cambio_password` y `bloqueo_cuenta`), comprobando que:

* Se genere un asunto válido.
* Las variables del contexto se inserten correctamente tanto en el HTML como en el texto plano.
* El texto `"Correo automático, no respondas."` esté presente en ambas versiones.

**Prueba 2:** `test_total_plantillas_es_cinco`

Verifica que el catálogo `PLANTILLAS_CORREO` contenga exactamente las 5 plantillas requeridas.

**Prueba 3:** `test_plantilla_desconocida_lanza_error`

Verifica que `renderizar_plantilla_correo()` lance un `ValueError` cuando se solicita una plantilla inexistente.

**Prueba 4:** `test_canal_correo_envia_html_multiparte`

Verifica que `CanalCorreo` envíe un correo multiparte con cuerpo `text/plain` y alternativa adjunta `text/html` utilizando el backend en memoria de Django.

**Comandos ejecutados:**

```bash
python -m pytest notificaciones/tests/ -v
ruff check notificaciones/

```

**Resultado obtenido:**

```text
collected 32 items

notificaciones/tests/test_plantillas_correo.py::test_renderizar_5_plantillas_con_pie_comun[activacion-contexto0-987654] PASSED
notificaciones/tests/test_plantillas_correo.py::test_renderizar_5_plantillas_con_pie_comun[bienvenida-contexto1-Daniel] PASSED
notificaciones/tests/test_plantillas_correo.py::test_renderizar_5_plantillas_con_pie_comun[recuperacion_password-contexto2-456123] PASSED
notificaciones/tests/test_plantillas_correo.py::test_renderizar_5_plantillas_con_pie_comun[cambio_password-contexto3-18/11/2026] PASSED
notificaciones/tests/test_plantillas_correo.py::test_renderizar_5_plantillas_con_pie_comun[bloqueo_cuenta-contexto4-30 minutos] PASSED
notificaciones/tests/test_plantillas_correo.py::test_total_plantillas_es_cinco PASSED
notificaciones/tests/test_plantillas_correo.py::test_plantilla_desconocida_lanza_error PASSED
notificaciones/tests/test_plantillas_correo.py::test_canal_correo_envia_html_multiparte PASSED

32 passed in 14.39s
All checks passed!

```

### 6. Resultado final

La creación de las 5 plantillas de correo, su integración con `CanalCorreo` y las pruebas automatizadas finalizaron correctamente.

Se verificó que:

* Las 5 plantillas heredan de `base.html` e incluyen el pie `"Correo automático, no respondas."`.
* La función `renderizar_plantilla_correo()` genera tanto texto plano como HTML válido.
* `CanalCorreo` soporta el envío multiparte sin afectar la retrocompatibilidad de pruebas anteriores.
* Las 32 pruebas de la suite de `notificaciones` y la revisión de estilo con `ruff` pasaron sin errores.

**Resultado:** 32 pruebas aprobadas (8 nuevas de plantillas + 24 existentes), 0 fallidas.

### 7. Dependencias y coordinación

Esta subtarea se apoya directamente en la clase `CanalCorreo` implementada en la **ST-41** (`EmailMultiAlternatives`) y mantiene compatibilidad con la selección dinámica de canales (`t-10/st-51`).

Se conservó intacta la firma base de `Canal.enviar()` agregando `html` como parámetro opcional para no afectar el funcionamiento de `CanalConsola`, `CanalWhatsApp` ni las pruebas existentes del worker de notificaciones.

**ST-42 finalizada.**

**Responsable de la actividad:** Daniel Orlando Ceja Olloqui (22420448).