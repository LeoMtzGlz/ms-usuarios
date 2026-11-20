# ST-192: Revisión de mensajes de los endpoints de autenticación

**Historia:** HU-27 — Recibir errores claros que no revelan información  
**Subtarea:** ST-192 — Revisar los mensajes de todos los endpoints de autenticación  
**Rama:** `t-27/st-192`  
**Estado del análisis:** Revisión documental; hallazgos pendientes de validación mediante pruebas comparativas.

## 1. Objetivo

Revisar las respuestas de los endpoints de autenticación para identificar si permiten distinguir entre una cuenta existente y una inexistente.

La descripción de ST-192 solicita comparar ambas respuestas. La HU-27 establece que login, recuperación y reenvío no deben revelar si una cuenta existe.

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

**Hallazgo:** la respuesta permite conocer si un correo o teléfono ya está registrado. Este comportamiento se documenta como exposición de información sobre las cuentas existentes.

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

**Ruta propuesta:** `POST /api/v1/auth/login/`  
**Estado:** En revisión; no integrado en `development` al momento de la consulta.

El PR #67 agrega `CustomTokenObtainPairView` y `CustomTokenObtainPairSerializer`.

Comportamiento descrito por el código del PR:

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

**Hallazgo:** las respuestas de cuenta pendiente e inactiva son distintas de la respuesta de credenciales inválidas. Por tanto, el endpoint propuesto puede revelar el estado de una cuenta existente.

Las pruebas incluidas en el PR cubren éxito, credenciales inválidas, cuenta pendiente y cuenta inactiva. Sin embargo, no comparan expresamente la respuesta de una cuenta existente con contraseña incorrecta contra la respuesta de una cuenta inexistente.

Referencia: [PR #67 — Crear el endpoint de login](https://github.com/LeoMtzGlz/ms-usuarios/pull/67).

## 3. Flujos no localizados en las rutas revisadas

En `usuarios/urls.py` y `config/urls.py` no se localizaron rutas para:

- Recuperación de contraseña.
- Reenvío de códigos de activación.

Por ello, no es posible evaluar todavía sus respuestas ni afirmar que cumplen el criterio de HU-27.

## 4. Hallazgos generales

1. El registro revela si un correo o teléfono está registrado mediante mensajes específicos.
2. El login propuesto diferencia cuentas pendientes e inactivas de credenciales inválidas.
3. Los endpoints 2FA revisados requieren autenticación y comunican estados del dispositivo.
4. No se localizaron los endpoints de recuperación y reenvío en las rutas inspeccionadas.
5. Se necesitan pruebas comparativas para verificar que las respuestas de login no revelen la existencia de una cuenta.

## 5. Recomendaciones

- Revisar el comportamiento del login antes de integrar el PR #67.
- Evaluar el uso de una respuesta externa genérica para los estados de cuenta que no deben revelarse.
- Conservar los detalles específicos para diagnóstico interno cuando corresponda, sin exponerlos en la respuesta pública.
- Comparar las respuestas HTTP y los cuerpos JSON de cuentas existentes e inexistentes.
- Completar el inventario cuando estén disponibles los endpoints de recuperación y reenvío.

## 6. Estado de la revisión

ST-192 cuenta con una revisión inicial de los endpoints de registro y 2FA integrados, así como del login propuesto en el PR #67.

La revisión no se considera exhaustiva: faltan los flujos de recuperación y reenvío y las pruebas comparativas de respuestas. La subtarea ST-194 contempla las pruebas de respuestas idénticas para cuentas existentes e inexistentes.

**Conclusión:** se identificaron respuestas que pueden revelar información de cuentas existentes. Los hallazgos deben atenderse y validarse antes de considerar cumplido el objetivo de HU-27.