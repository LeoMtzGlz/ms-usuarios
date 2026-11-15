# T-30

## ST-205
Implementación de autenticación de dos factores (2FA)

## 1. Descripción general

Esta historia de usuario implementa la funcionalidad de autenticación de dos factores (2FA) en el microservicio de usuarios.

El objetivo es permitir que un usuario configure un segundo factor de autenticación mediante una aplicación compatible con TOTP (*Time-Based One-Time Password*), como Google Authenticator, Microsoft Authenticator o Authy.

Para proteger la información de autenticación, el secreto generado para cada dispositivo se almacena cifrado en la base de datos.

## 2. Objetivos

- Generar secretos únicos para la configuración de 2FA de cada usuario.
- Proteger los secretos mediante cifrado Fernet.
- Generar una URI de aprovisionamiento compatible con aplicaciones autenticadoras.
- Verificar códigos TOTP generados por las aplicaciones autenticadoras.
- Almacenar la información del dispositivo asociado a cada usuario.
- Evitar guardar secretos de autenticación en texto plano.

## 3. Tecnologías y dependencias

| Tecnología | Uso |
|---|---|
| Python | Lenguaje de programación |
| Django | Framework del microservicio |
| PostgreSQL | Base de datos |
| PyOTP | Generación y validación de códigos TOTP |
| Cryptography | Cifrado y descifrado mediante Fernet |
| Docker Compose | Ejecución del entorno de desarrollo |

Dependencias principales:

- `pyotp`: permite generar secretos, códigos TOTP y URI de aprovisionamiento.
- `cryptography`: proporciona el mecanismo de cifrado Fernet para proteger los secretos almacenados.

## 4. Modelo de datos

Se incorpora el modelo `Dispositivo2FA` en `usuarios/models.py`.

Este modelo mantiene una relación uno a uno con el usuario, de manera que cada usuario tenga asociado un dispositivo de autenticación.

### Campos del modelo

| Campo | Tipo | Descripción |
|---|---|---|
| `usuario` | OneToOneField | Usuario propietario del dispositivo 2FA. |
| `secreto_cifrado` | TextField | Secreto TOTP almacenado mediante cifrado Fernet. |
| `confirmado` | BooleanField | Indica si el dispositivo fue confirmado. |
| `ultimo_intervalo` | BigIntegerField | Permite registrar el último intervalo TOTP utilizado. |
| `creado_en` | DateTimeField | Fecha de creación del dispositivo. |
| `confirmado_en` | DateTimeField | Fecha de confirmación del dispositivo. |

### Relación con el usuario

La relación `OneToOneField` garantiza que un usuario no tenga más de un registro de dispositivo 2FA asociado.

Además, se utiliza `on_delete=models.CASCADE`, por lo que el registro del dispositivo se elimina cuando se elimina el usuario relacionado.

## 5. Generación y protección del secreto

Cuando se inicia la configuración de 2FA, el sistema genera un secreto aleatorio utilizando PyOTP.

El secreto se utiliza posteriormente para generar y validar los códigos temporales de autenticación.

Para protegerlo, se utiliza el mecanismo de cifrado Fernet de la biblioteca `cryptography`.

El proceso funciona de la siguiente manera:

1. Se genera un secreto aleatorio mediante `pyotp.random_base32()`.
2. El secreto se cifra utilizando la función `cifrar()`.
3. El resultado cifrado se almacena en el campo `secreto_cifrado`.
4. Cuando se necesita utilizar el secreto, se recupera mediante la propiedad `secreto`, que utiliza la función `descifrar()`.

De esta manera, el secreto original no se almacena directamente en la base de datos.

### Módulo de cifrado

La lógica de cifrado y descifrado se encuentra en:

`comun/cifrado.py`

Se implementan dos funciones principales:

- `cifrar(texto)`: recibe un texto y devuelve su versión cifrada mediante Fernet.
- `descifrar(token)`: recibe un texto cifrado y devuelve el contenido original.

La clave Fernet se obtiene desde la configuración de Django, evitando escribirla directamente en el código fuente.

## 6. Configuración de variables de entorno

La implementación requiere una clave Fernet para cifrar y descifrar los secretos de autenticación.

Se utiliza la variable:

`CLAVE_CIFRADO_2FA`

Esta variable debe configurarse en el archivo `.env` del entorno de ejecución.

Para generar una clave Fernet se puede ejecutar:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Después, se agrega la clave generada al archivo `.env`:

```ini
CLAVE_CIFRADO_2FA=clave_fernet_generada
```

En el archivo `.env.example` únicamente debe incluirse la variable sin una clave real:

```ini
CLAVE_CIFRADO_2FA=
```

**Importante:** La clave Fernet debe mantenerse privada y no debe subirse al repositorio. Si se pierde o cambia, los secretos cifrados con la clave anterior no podrán descifrarse.

También se utiliza la variable `ISSUER_2FA` para identificar al servicio en las aplicaciones autenticadoras.

## 7. Aprovisionamiento del dispositivo

El modelo `Dispositivo2FA` incluye el método `uri_aprovisionamiento()`.

Este método genera una URI compatible con aplicaciones autenticadoras utilizando:

- El secreto del usuario.
- El correo electrónico del usuario.
- El identificador del servicio configurado en `ISSUER_2FA`.

La URI se genera mediante el método `provisioning_uri()` de PyOTP.

Esta URI puede utilizarse posteriormente para generar un código QR que el usuario escanee desde su aplicación autenticadora.

## 8. Verificación de códigos TOTP

El modelo implementa el método `verificar(codigo)`, que utiliza PyOTP para comprobar si un código proporcionado corresponde al secreto almacenado.

La verificación se realiza mediante `pyotp.TOTP` y utiliza `valid_window=1` para aceptar una pequeña ventana de tolerancia temporal.

Esto permite compensar pequeñas diferencias de sincronización entre el servidor y el dispositivo del usuario.

## 9. Migraciones de base de datos

Se incorpora una migración para crear la tabla correspondiente al modelo `Dispositivo2FA`.

La migración depende de la migración `0003_codigoverificacion`, debido a que ambas modificaciones forman parte del historial de cambios del microservicio.

La migración correspondiente a esta historia de usuario es:

`usuarios/migrations/0004_dispositivo2fa.py`

Para aplicar las migraciones en el entorno Docker:

```bash
docker compose exec api python manage.py migrate
```

Para comprobar si existen cambios en los modelos que todavía no estén registrados en migraciones:

```bash
docker compose exec api python manage.py makemigrations --check --dry-run
```

## 10. Pruebas

Se incorporan pruebas automatizadas en:

`usuarios/tests/test_dispositivo2fa.py`

Las pruebas contemplan los siguientes escenarios:

| Prueba | Resultado esperado |
|---|---|
| Cifrar y descifrar un secreto | Recuperar el texto original. |
| Almacenar un secreto en la base de datos | Comprobar que el valor almacenado no sea texto plano. |
| Verificar un código TOTP válido | La verificación debe devolver `True`. |
| Rechazar un código TOTP incorrecto | La verificación debe devolver `False`. |

### Ejecución de las pruebas

Para ejecutar únicamente las pruebas de esta historia de usuario:

```bash
docker compose exec api python manage.py test usuarios.tests.test_dispositivo2fa
```

Para ejecutar todas las pruebas del módulo de usuarios:

```bash
docker compose exec api python manage.py test usuarios.tests
```

Resultados
- Pruebas de cifrado y descifrado: Correctas.
- Pruebas de almacenamiento cifrado: Correctas.
- Pruebas de validación TOTP: Correctas.
- Pruebas de rechazo de códigos incorrectos: Correctas.

## 11. Consideraciones de seguridad

- Los secretos TOTP no deben almacenarse en texto plano.
- La clave Fernet debe mantenerse en variables de entorno.
- No se debe incluir la clave de cifrado real en el repositorio.
- La URI de aprovisionamiento contiene información sensible y no debe exponerse innecesariamente.
- La tolerancia temporal de TOTP permite aceptar códigos de intervalos cercanos; por ello, las reglas adicionales de prevención de reutilización deben contemplarse en la implementación correspondiente.

## 12. Archivos involucrados

| Archivo | Responsabilidad |
|---|---|
| `usuarios/models.py` | Definición del modelo `Dispositivo2FA` y sus métodos. |
| `comun/cifrado.py` | Funciones de cifrado y descifrado Fernet. |
| `settings.py` | Configuración de las variables `CLAVE_CIFRADO_2FA` e `ISSUER_2FA`. |
| `.env.example` | Declaración de las variables de entorno necesarias. |
| `usuarios/migrations/0004_dispositivo2fa.py` | Creación del modelo en la base de datos. |
| `usuarios/tests/test_dispositivo2fa.py` | Pruebas automatizadas de la funcionalidad. |

## 13. Alcance de la implementación

Esta historia de usuario establece la estructura necesaria para gestionar dispositivos 2FA, proteger los secretos de autenticación y verificar códigos TOTP.

La activación y desactivación completa del segundo factor, así como las reglas adicionales de prevención de reutilización de códigos y su integración en el flujo de inicio de sesión, deben documentarse e implementarse según las historias de usuario correspondientes.