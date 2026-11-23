# Documentación de las configuraciones implementadas: verificación en dos pasos (2FA)

## 1. Objetivo general

Se incorporó al servicio de usuarios el flujo inicial para activar la **verificación en dos pasos (2FA)** mediante códigos temporales de seis dígitos (TOTP), generados por una aplicación autenticadora.

La implementación separa el proceso en dos operaciones:

1. **Iniciar la activación:** generar un secreto asociado al usuario y entregar los datos necesarios para registrar la cuenta en una aplicación autenticadora.
2. **Confirmar la activación:** comprobar que el usuario puede generar un código válido con ese secreto. El 2FA solo queda habilitado después de esta comprobación.

Esta separación evita que la cuenta quede marcada como protegida antes de que el usuario haya configurado correctamente su aplicación autenticadora.

## 2. Archivos modificados y creados

| Archivo | Cambio realizado | Propósito |
|---|---|---|
| `requirements.txt` | Se agregó `qrcode[pil]` | Incorporar la generación de imágenes QR. |
| `comun/errores.py` | Se agregaron dos excepciones | Representar los casos en los que el 2FA ya está activo o todavía no se ha iniciado. |
| `docs/catalogo-errores.md` | Se documentaron dos códigos | Mantener actualizado el catálogo de errores de la API. |
| `usuarios/serializers.py` | Se agregó `CodigoDosFactoresSerializer` | Validar el formato del código TOTP recibido. |
| `usuarios/dos_factores.py` | Archivo nuevo | Convertir la URI de aprovisionamiento en una imagen QR codificada en Base64. |
| `usuarios/views_2fa.py` | Archivo nuevo | Implementar los endpoints para iniciar y confirmar la activación. |
| `usuarios/urls.py` | Se agregaron dos rutas | Exponer los endpoints de 2FA en la API. |
| `usuarios/tests/test_2fa_endpoints.py` | Archivo nuevo | Verificar los escenarios principales del flujo mediante pruebas automatizadas. |

Las vistas se colocaron en `views_2fa.py` en lugar de modificar el `views.py` existente. La intención fue reducir los conflictos de Git mientras otros integrantes del equipo trabajan en ese archivo. Si el equipo decide centralizar las vistas, pueden trasladarse sin cambiar la lógica descrita.

---

## 3. Descripción de los cambios

### 3.1. Dependencia para generar códigos QR

**Archivo:** `requirements.txt`

Se agregó:

```text
qrcode[pil]
```

Esta dependencia permite generar una imagen QR a partir de una URI. La opción `[pil]` instala el soporte necesario para producir la imagen mediante Pillow.

El QR contiene la información de aprovisionamiento que la aplicación autenticadora necesita para registrar el secreto del usuario. Así, el usuario puede escanearlo en lugar de introducir manualmente la configuración.

Para instalar la dependencia:

```bash
pip install "qrcode[pil]"
```

Si el proyecto se ejecuta con Docker, se debe reconstruir la imagen del servicio correspondiente:

```bash
docker compose build api
```

También se indicó fijar en `requirements.txt` la versión instalada, siguiendo el criterio utilizado con las demás dependencias del proyecto.

### 3.2. Nuevos errores del catálogo

**Archivo:** `comun/errores.py`

Se añadieron dos excepciones:

- `DosFactoresYaActivo`
  - Código: `dos_factores_ya_activo`
  - Mensaje: “La verificación en dos pasos ya está activa en tu cuenta.”
  - Se utiliza cuando se intenta iniciar o confirmar nuevamente un 2FA que ya fue confirmado.

- `DosFactoresNoIniciado`
  - Código: `dos_factores_no_iniciado`
  - Mensaje: “Primero solicita la activación de la verificación en dos pasos.”
  - Se utiliza cuando se intenta confirmar el 2FA sin haber iniciado antes el proceso.

Ambas excepciones heredan de `ValidationError` de Django REST Framework, por lo que se manejan como errores de validación de la API.

**Archivo:** `docs/catalogo-errores.md`

Se indicó agregar ambos códigos al catálogo y documentarlos con estado HTTP **400**. Esto permite que los clientes de la API identifiquen de forma consistente por qué no se pudo completar la operación.

### 3.3. Validación del código de autenticación

**Archivo:** `usuarios/serializers.py`

Se agregó `CodigoDosFactoresSerializer`, que recibe el campo `codigo` y comprueba que tenga exactamente seis dígitos numéricos mediante una expresión regular:

```python
r"^\d{6}$"
```

Por tanto:

- `123456` cumple el formato.
- `12345` no cumple porque tiene cinco dígitos.
- `1234567` no cumple porque tiene siete dígitos.
- `12ab56` no cumple porque contiene letras.

Esta validación comprueba únicamente la estructura del dato. Que el código tenga seis dígitos no significa que sea correcto: su validez se comprueba posteriormente contra el secreto del usuario.

Si el formato no es válido, el serializer genera un error de validación antes de intentar verificar el código TOTP.

### 3.4. Generación de la imagen QR

**Archivo nuevo:** `usuarios/dos_factores.py`

Se creó la función:

```python
qr_base64(uri: str) -> str
```

Su responsabilidad es recibir una URI de aprovisionamiento `otpauth://` y devolver la imagen QR en formato PNG codificada en Base64, sin anteponer el prefijo `data:`.

El procedimiento es:

1. `qrcode.make(uri)` genera la imagen QR a partir de la URI.
2. `io.BytesIO()` crea un buffer en memoria para almacenar la imagen sin tener que guardarla como archivo.
3. `imagen.save(buffer, format="PNG")` escribe la imagen en formato PNG dentro del buffer.
4. `buffer.getvalue()` obtiene los bytes de la imagen.
5. `base64.b64encode(...)` convierte esos bytes a Base64.
6. `.decode()` convierte el resultado a una cadena de texto.

El resultado puede enviarse en la respuesta JSON de la API para que el cliente lo utilice y muestre como imagen QR.

### 3.5. Endpoint para iniciar la activación

**Archivo nuevo:** `usuarios/views_2fa.py`

**Ruta:** `POST /api/v1/auth/2fa/activar/`

La vista `Activar2FAView` inicia el registro de un dispositivo de autenticación para el usuario que realiza la solicitud.

El flujo implementado es:

1. Abre una transacción de base de datos con `transaction.atomic()`.
2. Busca el dispositivo 2FA del usuario mediante `select_for_update()`, que bloquea el registro durante la transacción para evitar modificaciones concurrentes sobre ese registro.
3. Si no existe un dispositivo, crea una instancia nueva de `Dispositivo2FA`.
4. Comprueba si el dispositivo ya está confirmado. Si lo está, responde con el error `dos_factores_ya_activo`.
5. Si todavía no está confirmado, genera un secreto nuevo mediante `dispositivo.generar_secreto()` y guarda el dispositivo.
6. Obtiene la URI de aprovisionamiento con `dispositivo.uri_aprovisionamiento()`.
7. Registra el evento `2fa_activacion_iniciada`.
8. Devuelve el secreto, la URI y el QR codificado en Base64.

La respuesta tiene esta estructura:

```json
{
  "secreto": "...",
  "uri": "otpauth://totp/...",
  "qr_base64": "..."
}
```

**Comportamiento importante:** iniciar la activación no habilita todavía el 2FA. El dispositivo permanece sin confirmar hasta que el usuario envía un primer código válido.

Si el usuario vuelve a solicitar la activación antes de confirmar, se genera un secreto nuevo y el anterior deja de ser el secreto vigente para ese dispositivo. Esto permite reiniciar el proceso de configuración.

El código también incluye un comentario de seguridad: el secreto se devuelve en esta respuesta para que el usuario pueda configurar su aplicación, pero no debe incluirse en la bitácora ni en los logs.

### 3.6. Endpoint para confirmar la activación

**Archivo:** `usuarios/views_2fa.py`

**Ruta:** `POST /api/v1/auth/2fa/confirmar/`

La vista `Confirmar2FAView` recibe el código de seis dígitos generado por la aplicación autenticadora y determina si el usuario configuró correctamente el dispositivo.

Ejemplo de cuerpo de la solicitud:

```json
{
  "codigo": "123456"
}
```

El flujo es:

1. Valida el cuerpo de la solicitud con `CodigoDosFactoresSerializer`.
2. Inicia una transacción y busca el dispositivo 2FA del usuario utilizando `select_for_update()`.
3. Si no existe un dispositivo, genera el error `dos_factores_no_iniciado`.
4. Si el dispositivo ya está confirmado, genera el error `dos_factores_ya_activo`.
5. Ejecuta `dispositivo.verificar(codigo)` para comprobar el código recibido.
6. Si el código es válido:
   - Marca `confirmado` como `True`.
   - Guarda la fecha y hora en `confirmado_en`.
   - Actualiza `ultimo_intervalo` con el intervalo TOTP actual.
   - Guarda únicamente los campos modificados.
7. Si el código no es válido, registra `2fa_confirmacion_fallida` y responde con `CodigoInvalido`.
8. Si la confirmación es correcta, registra `2fa_activado` y devuelve una respuesta de éxito.

La respuesta de éxito es:

```json
{
  "confirmado": true,
  "mensaje": "Verificación en dos pasos activada."
}
```

**Intervalo TOTP:** se definió `PASO_TOTP = 30`, por lo que cada código tiene un intervalo de 30 segundos. Al guardar el intervalo utilizado en `ultimo_intervalo`, la implementación evita reutilizar el mismo intervalo de código en el flujo previsto por la historia HU-31.

**Transacciones y eventos:** las operaciones que modifican el dispositivo se realizan dentro de una transacción. Los eventos de confirmación se registran después del bloque transaccional, de acuerdo con los comentarios de la implementación.

También se dejó indicado que los códigos de respaldo de la historia ST-207 se generarán posteriormente y se agregarán a la respuesta una sola vez. Esa funcionalidad no forma parte de lo implementado en este cambio.

### 3.7. Registro de las rutas

**Archivo:** `usuarios/urls.py`

Se incorporaron las vistas nuevas al sistema de rutas:

```python
path("2fa/activar/", Activar2FAView.as_view(), name="2fa-activar"),
path("2fa/confirmar/", Confirmar2FAView.as_view(), name="2fa-confirmar"),
```

Con el prefijo de autenticación utilizado en el proyecto, las rutas completas son:

- `POST /api/v1/auth/2fa/activar/`
- `POST /api/v1/auth/2fa/confirmar/`

La instrucción original indica agregar estas rutas sin eliminar las que ya existan en el archivo, especialmente si otros integrantes del equipo incorporaron endpoints adicionales.

### 3.8. Pruebas automatizadas

**Archivo nuevo:** `usuarios/tests/test_2fa_endpoints.py`

Se creó un conjunto de pruebas con `pytest`, `APIClient` y `UsuarioFactory` para comprobar el comportamiento de los endpoints.

Se utiliza `pytest.mark.django_db` para habilitar el acceso a la base de datos durante las pruebas.

También se agregó una fixture que genera una clave Fernet temporal y la asigna a `settings.CLAVE_CIFRADO_2FA`. Esto permite ejecutar las pruebas con una clave de cifrado disponible.

La fixture `sesion` crea un usuario, instancia un cliente de API y lo autentica para probar las solicitudes como usuario con sesión autenticada.

Las pruebas cubren estos escenarios:

| Prueba | Qué verifica |
|---|---|
| `test_activar_exige_sesion` | Que el endpoint de activación rechace una solicitud sin autenticación con estado 401. |
| `test_activar_devuelve_secreto_uri_y_qr` | Que la activación devuelva el secreto, una URI `otpauth://` y un QR cuyo contenido Base64 corresponde a un PNG. |
| `test_el_secreto_se_guarda_cifrado_y_sin_confirmar` | Que el secreto se almacene cifrado y que el dispositivo todavía no esté confirmado. |
| `test_activar_otra_vez_antes_de_confirmar_cambia_el_secreto` | Que una nueva solicitud de activación genere un secreto diferente mientras el proceso siga sin confirmar. |
| `test_confirmar_con_codigo_correcto_activa_el_2fa` | Que un código TOTP válido active el dispositivo. |
| `test_confirmar_con_codigo_incorrecto_no_activa` | Que un código incorrecto produzca un error y no active el dispositivo. |
| `test_confirmar_sin_haber_activado` | Que no se pueda confirmar si no existe un proceso de activación iniciado. |
| `test_confirmar_con_formato_invalido` | Que un código que no tenga seis dígitos numéricos sea rechazado por la validación. |
| `test_no_se_puede_activar_si_ya_esta_confirmado` | Que no se permita iniciar nuevamente la activación cuando el 2FA ya está confirmado. |

La función auxiliar `codigo_incorrecto` se simplificó para probar algunos códigos candidatos y devolver uno que no sea válido para el secreto generado:

```python
def codigo_incorrecto(secreto):
    totp = pyotp.TOTP(secreto)
    return next(
        c for c in ("000000", "111111", "222222")
        if not totp.verify(c, valid_window=1)
    )
```

También se indicó eliminar los imports que no se utilicen en el archivo de pruebas.

Para ejecutar únicamente estas pruebas dentro del contenedor del servicio API:

```bash
docker compose run --rm api pytest usuarios/tests/test_2fa_endpoints.py
```

---

## 4. Flujo completo de funcionamiento

El proceso de activación queda organizado de la siguiente manera:

1. El usuario autenticado solicita `POST /api/v1/auth/2fa/activar/`.
2. El backend genera y almacena el secreto del dispositivo.
3. El backend construye la URI de aprovisionamiento y genera el QR.
4. El cliente recibe el secreto, la URI y el QR, y muestra el QR al usuario.
5. El usuario escanea el QR con su aplicación autenticadora.
6. La aplicación genera un código temporal de seis dígitos.
7. El usuario envía ese código a `POST /api/v1/auth/2fa/confirmar/`.
8. El backend valida el formato y verifica el código contra el secreto guardado.
9. Si el código es correcto, el backend marca el dispositivo como confirmado y registra el evento de activación.
10. Si el código es incorrecto, el dispositivo permanece sin confirmar y se registra el intento fallido.

## 5. Consideraciones de seguridad contempladas

De acuerdo con el código proporcionado, se contemplan las siguientes medidas:

- **Secreto almacenado cifrado:** la prueba correspondiente comprueba que el valor almacenado en `secreto_cifrado` no sea igual al secreto en texto plano y que la propiedad `secreto` permita recuperar el valor esperado.
- **Confirmación explícita:** el 2FA no se activa solo por generar un secreto o mostrar el QR.
- **Validación de entrada:** el código debe contener exactamente seis dígitos.
- **Control de estado:** se impide confirmar sin iniciar el proceso y volver a activar un dispositivo ya confirmado.
- **Bloqueo de registro durante operaciones:** se utiliza `select_for_update()` dentro de transacciones para proteger las operaciones sobre el dispositivo.
- **Registro de eventos:** se registran el inicio, la confirmación exitosa y la confirmación fallida.
- **Protección del secreto en logs:** el comentario de implementación indica expresamente que el secreto no debe enviarse a la bitácora ni a los logs.
- **Control del intervalo TOTP:** se guarda el último intervalo utilizado para evitar la reutilización del código en el mismo intervalo, conforme al comportamiento indicado en el código.

## 6. Alcance de lo realizado y pendientes identificados

Este conjunto de cambios implementa el **inicio y la confirmación de la activación del 2FA**. No debe interpretarse como la implementación completa de todos los procesos relacionados con la autenticación en dos pasos.

El propio código deja identificados estos puntos:

- **Códigos de respaldo (ST-207):** se indica que se generarán posteriormente y se devolverán una sola vez. No están implementados en estas vistas.
- **Uso del 2FA durante el inicio de sesión:** el material proporcionado no muestra cambios al flujo de login para exigir un segundo factor después de validar la contraseña.
- **Desactivación o recuperación del 2FA:** no se muestran endpoints para desactivar el dispositivo o recuperar el acceso.
- **Interfaz del cliente:** el material describe las respuestas de la API, pero no incluye la implementación de pantallas para mostrar el QR o capturar el código.

Estos puntos se mencionan como límites del contenido revisado; no se afirma que estén pendientes en todo el proyecto, ya que podrían estar implementados en otros archivos o historias.

## 7. Resumen

En conjunto, los cambios agregan al servicio de usuarios dos endpoints para configurar y confirmar la verificación en dos pasos mediante TOTP. Se incorporó la generación de códigos QR, la validación del código de seis dígitos, el manejo de errores específicos, el registro de eventos y un conjunto de pruebas automatizadas para los escenarios principales.

La decisión central del diseño es que **el 2FA solo se considera activo después de que el usuario demuestra que configuró correctamente su aplicación autenticadora**, enviando un código válido generado con el secreto entregado durante el inicio de la activación.
