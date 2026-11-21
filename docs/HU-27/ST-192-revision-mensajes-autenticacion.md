# ST-192: Revisión de mensajes de los endpoints de autenticación

**Historia:** HU-27 — Recibir errores claros que no revelan información  
**Subtarea:** ST-192 — Revisar los mensajes de todos los endpoints de autenticación  
**Rama:** `t-27/st-192`  
**Estado del análisis:** Revisión documental de los flujos integrados en `development` y de los cambios propuestos en PR relacionados con autenticación. Los hallazgos comparativos pendientes corresponden a ST-194.

## 1. Objetivo

Revisar las respuestas de los endpoints de autenticación para identificar si permiten distinguir entre una cuenta existente y una inexistente.

La descripción de ST-192 solicita comparar ambas respuestas. La HU-27 establece que los flujos de login, recuperación y reenvío no deben revelar si una cuenta existe.

## 2. Endpoints revisados

### 2.1 Registro

**Ruta:** `POST /api/v1/auth/registro/`  
**Estado:** Implementado en `development`.

Comportamiento observado:

| Situación | HTTP | Respuesta |
|---|---:|---|
| Registro válido | 201 | Devuelve los datos públicos de la cuenta |
| Correo ya registrado | 400 | `datos_invalidos` |
| Teléfono ya registrado | 400 | `datos_invalidos` |

Para los datos duplicados, el serializer utiliza mensajes específicos:

- `Este correo ya está registrado.`
- `Este teléfono ya está registrado.`

**Hallazgo:** la respuesta informa si un correo o teléfono ya está registrado. En el flujo de registro, este mensaje permite comunicar que los datos no pueden utilizarse para crear otra cuenta.

La mitigación ante intentos de enumeración contempla los límites de solicitudes definidos en ST-179 y ST-180. La implementación de ST-180 se encuentra en el PR #71 y todavía no está integrada en `development`.

### 2.2 Activación de 2FA

**Ruta:** `POST /api/v1/auth/2fa/activar/`  
**Estado:** Implementado en `development`.

Requiere una sesión autenticada.

| Situación | HTTP | Código |
|---|---:|---|
| Activación iniciada correctamente | 200 | Respuesta con secreto, URI y QR |
| 2FA ya confirmado | 400 | `dos_factores_ya_activo` |
| Sin sesión | 401 | No especificado en las pruebas revisadas |

El secreto se almacena cifrado. La vista registra el evento de inicio de activación, sin incluir el secreto en la bitácora.

### 2.3 Confirmación de 2FA

**Ruta:** `POST /api/v1/auth/2fa/confirmar/`  
**Estado:** Implementado en `development`.

Requiere una sesión autenticada.

| Situación | HTTP | Código |
|---|---:|---|
| Código correcto | 200 | `confirmado: true` |
| Código incorrecto | 400 | `codigo_invalido` |
| No se inició la activación | 400 | `dos_factores_no_iniciado` |
| Código con formato inválido | 400 | `datos_invalidos` |
| 2FA ya confirmado | 400 | `dos_factores_ya_activo` |

Estos mensajes describen el estado del dispositivo 2FA de una cuenta autenticada. Las pruebas revisadas no comparan cuentas existentes e inexistentes.

### 2.4 Inicio de sesión — PR #67

**Ruta:** `POST /api/v1/auth/login/`  
**Estado:** Integrado en `development` mediante el PR #67.

Comportamiento observado:

| Situación | HTTP | Código |
|---|---:|---|
| Usuario inexistente o contraseña incorrecta | 401 | `credenciales_invalidas` |
| Cuenta pendiente | 403 | `cuenta_pendiente` |
| Cuenta inactiva | 403 | `cuenta_inactiva` |
| Inicio de sesión correcto | 200 | Devuelve JWT y datos del usuario |

Mensajes del catálogo de errores:

- `credenciales_invalidas`: “Correo, teléfono o contraseña incorrectos.”
- `cuenta_pendiente`: “Tu cuenta aún no está activa. Escribe el código que te enviamos.”
- `cuenta_inactiva`: “Tu cuenta está desactivada. Contacta al administrador.”

El backend permite buscar por correo o teléfono. Cuando no encuentra al usuario, calcula un hash ficticio antes de rechazar las credenciales.

**Hallazgo:** los mensajes de cuenta pendiente e inactiva se devuelven únicamente después de que la contraseña proporcionada fue validada correctamente. Por lo tanto, una persona que desconoce la contraseña no puede utilizar esas respuestas para confirmar la existencia de una cuenta ni conocer su estado.

Además, HU-05 solicita explícitamente informar cuando una cuenta está pendiente o inactiva. Por este motivo, estos mensajes forman parte del comportamiento esperado del login y no se consideran una exposición de información para quien no conoce las credenciales.

Las pruebas incluidas en el PR cubren éxito, credenciales inválidas, cuenta pendiente y cuenta inactiva. La comparación específica de respuestas para cuentas existentes e inexistentes corresponde a las pruebas contempladas en ST-194.

Referencia: [PR #67 — Crear el endpoint de login](https://github.com/LeoMtzGlz/ms-usuarios/pull/67).

## 3. Flujos no integrados o no localizados en las rutas revisadas

### 3.1 Recuperación de contraseña — PR #79

**Ruta propuesta:** `POST /api/v1/auth/recuperar/`  
**Estado:** Propuesto en el PR #79; todavía no integrado en `development`.

De acuerdo con la descripción del PR, el endpoint recibe un identificador que puede ser correo o teléfono y responde con HTTP 200 y el mensaje:

`Si la cuenta existe, te enviamos un código.`

La respuesta se mantiene igual tanto si la cuenta existe como si no. También se contempla que los errores del proveedor de notificaciones se registren sin modificar la respuesta pública.

**Análisis:** el comportamiento propuesto evita revelar si el identificador pertenece a una cuenta registrada. Este flujo deberá revisarse nuevamente cuando el PR se integre en `development`.

Referencia: [PR #79 — Recuperación de contraseña](https://github.com/LeoMtzGlz/ms-usuarios/pull/79).

### 3.2 Reenvío de códigos

En las rutas revisadas de `usuarios/urls.py` y `config/urls.py` no se localizó un endpoint de reenvío de códigos de activación.

Por ello, no es posible evaluar todavía sus respuestas ni confirmar si mantiene un comportamiento equivalente para cuentas existentes e inexistentes.

## 4. Hallazgos generales

1. **Registro:** informa cuando un correo o teléfono ya está registrado. Es necesario comunicar que esos datos ya están en uso; la mitigación ante intentos de enumeración contempla los límites de solicitudes de ST-179 y ST-180. ST-180 sigue pendiente de integración mediante el PR #71.
2. **Login:** los mensajes de cuenta pendiente e inactiva aparecen únicamente después de validar correctamente la contraseña. Además, HU-05 solicita explícitamente estos mensajes, por lo que no se consideran una fuga de información para quien desconoce las credenciales.
3. **2FA:** los endpoints revisados requieren autenticación y comunican estados del dispositivo 2FA.
4. **Recuperación:** el PR #79 propone una respuesta genérica e idéntica para identificadores existentes e inexistentes, pero todavía no está integrado en `development`.
5. **Reenvío:** no se identificó el endpoint correspondiente en las rutas revisadas de `development`.

## 5. Recomendaciones

- Mantener los mensajes de cuenta pendiente e inactiva en el login, ya que se muestran después de validar correctamente la contraseña y corresponden al comportamiento solicitado por HU-05.
- Mantener una respuesta genérica en los flujos de recuperación y reenvío para evitar revelar si una cuenta existe.
- Conservar los detalles específicos para diagnóstico interno cuando corresponda, sin exponerlos en respuestas públicas.
- Considerar los límites de solicitudes definidos para mitigar intentos de enumeración durante el registro.
- Completar la revisión de recuperación y reenvío cuando esos endpoints estén integrados en `development`.
- Realizar las pruebas comparativas de respuestas contempladas en ST-194.

## 6. Estado de la revisión

ST-192 cuenta con una revisión documental de los endpoints de registro, login y 2FA integrados en `development`. También se consideró el comportamiento propuesto para recuperación de contraseña en el PR #79, diferenciándolo de los cambios ya integrados.

La revisión no sustituye las pruebas comparativas de respuestas para cuentas existentes e inexistentes, contempladas en ST-194. Tampoco permite confirmar el comportamiento del reenvío de códigos, cuyo endpoint no se localizó en las rutas revisadas.

**Conclusión:** los mensajes de cuenta pendiente e inactiva del login no se consideran una fuga de información porque se muestran únicamente después de validar correctamente la contraseña y son requeridos por HU-05. El mensaje de registro para correo o teléfono duplicado informa que los datos ya están en uso; la mitigación ante intentos de enumeración contempla los límites de solicitudes. La recuperación de contraseña cuenta con una propuesta de respuesta genérica en el PR #79, todavía pendiente de integración en `development`.