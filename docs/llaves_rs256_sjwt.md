# Llaves RS256 para los tokens JWT (T-04)

El microservicio de usuarios firma los tokens de sesión (JWT) con el algoritmo **RS256**. Esta guía explica qué son las llaves, cómo generarlas en tu máquina, cómo las usa Django y qué hacer cuando algo falla.

> **Regla de oro:** la llave privada **nunca** se sube a Git, ni se manda por chat, correo o Drive. Cada integrante genera la suya.

---

## ¿Qué es RS256 y por qué dos llaves?

RS256 es una firma **RSA con SHA-256**. A diferencia de HS256 (una sola clave secreta compartida), usa un **par de llaves**:

| Llave | Archivo | Quién la tiene | Para qué |
| --- | --- | --- | --- |
| **Privada** | `llaves/privada.pem` | Solo `ms-usuarios` | **Firmar** los tokens al iniciar sesión o renovarlos |
| **Pública** | `llaves/publica.pem` | `ms-usuarios` y cualquier otro microservicio | **Verificar** que un token es auténtico y no fue alterado |

Así, los demás microservicios (catálogo, pedidos...) pueden comprobar quién es cada persona con la llave pública, pero **no pueden fabricar tokens**: para eso hace falta la privada, que solo vive aquí.

```text
 Inicio de sesión                          Petición a otro servicio
┌───────────────┐   token firmado    ┌──────────┐   token    ┌──────────────────┐
│  ms-usuarios  │ ─────────────────▶ │ Frontend │ ─────────▶ │ catálogo/pedidos │
│ (privada.pem) │                    └──────────┘            │  (publica.pem)   │
└───────────────┘                                            └──────────────────┘
     firma                                                        verifica
```

---

## Requisitos

- **OpenSSL**. Para comprobar que lo tienes: `openssl version`.
  - **Linux y macOS:** ya viene instalado.
  - **Windows:** úsalo desde **Git Bash** (viene con Git). En PowerShell o CMD normalmente no está.
- Si no tienes OpenSSL, consulta [Alternativa sin OpenSSL](#alternativa-sin-openssl).

---

## Generar las llaves

Desde la raíz del proyecto (donde está `manage.py`):

```bash
# 1. Llave privada RSA de 2048 bits
openssl genrsa -out llaves/privada.pem 2048

# 2. Llave pública, derivada de la privada
openssl rsa -in llaves/privada.pem -pubout -out llaves/publica.pem

# 3. (Linux/macOS) Solo tu usuario puede leer la privada
chmod 600 llaves/privada.pem
```

Al terminar, la carpeta queda así:

```text
llaves/
├── .gitkeep       # lo único que se sube a Git
├── privada.pem    # -----BEGIN PRIVATE KEY-----   (ignorada)
└── publica.pem    # -----BEGIN PUBLIC KEY-----    (ignorada)
```

> Solo se hace **una vez**, al clonar el proyecto. Si borras las llaves, vuelve a generarlas (ver [Rotar las llaves](#rotar-las-llaves)).

---

## Comprobar que todo está bien

```bash
# La privada es válida (debe decir "RSA key ok")
openssl rsa -in llaves/privada.pem -check -noout

# La pública corresponde a la privada (no debe imprimir nada)
openssl rsa -in llaves/privada.pem -pubout | diff - llaves/publica.pem

# Git las ignora (debe mostrar la regla del .gitignore que las cubre)
git check-ignore -v llaves/privada.pem llaves/publica.pem

# Y no aparecen como archivos por subir
git status -u
```

---

## Cómo las usa el proyecto

### Variables de entorno

En `.env` (copiado de `.env.example`):

| Variable | Valor por defecto | Para qué |
| --- | --- | --- |
| `JWT_LLAVE_PRIVADA` | `llaves/privada.pem` | Ruta, relativa a la raíz del proyecto, de la llave que firma |
| `JWT_LLAVE_PUBLICA` | `llaves/publica.pem` | Ruta de la llave que verifica |

Con los valores por defecto no hace falta cambiar nada.

### Configuración de SimpleJWT (`config/settings.py`)

```python
from datetime import timedelta

LLAVE_PRIVADA = BASE_DIR / env("JWT_LLAVE_PRIVADA", default="llaves/privada.pem")
LLAVE_PUBLICA = BASE_DIR / env("JWT_LLAVE_PUBLICA", default="llaves/publica.pem")

SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": LLAVE_PRIVADA.read_text(),
    "VERIFYING_KEY": LLAVE_PUBLICA.read_text(),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

REST_FRAMEWORK = {
    # ...lo que ya existe...
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
```

Dependencias en `requirements.txt`:

```text
djangorestframework-simplejwt
cryptography   # sin ella SimpleJWT no puede firmar con RS256
```

### Con Docker

`docker-compose.yml` monta el proyecto completo en `/app`, así que el contenedor ve tus llaves en `/app/llaves/` sin hacer nada más.

La **imagen**, en cambio, nunca debe llevarlas: el `Dockerfile` hace `COPY . .`, por eso el `.dockerignore` excluye `llaves/`, `*.pem` y `.env`. En un servidor real las llaves se montan como volumen o secreto, no se copian a la imagen.

---

## Lo que cada integrante debe saber

- **Cada quien tiene sus propias llaves.** Un token generado en tu máquina **no** es válido en la de otra persona, y eso es lo esperado.
- **Si otro microservicio necesita verificar tokens**, se le comparte **solo** `publica.pem`. Nunca la privada.
- **En las pruebas automáticas y en GitHub Actions** se generan llaves temporales en cada ejecución. Nunca se guardan llaves reales como secreto del repositorio sin acuerdo del equipo.
- **Si una llave privada se sube por error** a Git, aunque sea en una rama, se considera comprometida: avisa al equipo, genera un par nuevo y pide que se limpie el historial. Borrarla en un commit nuevo **no basta**.

---

## Rotar las llaves

Hay que generar un par nuevo si la privada se filtró, se perdió, o cuando el equipo lo decida (por ejemplo, antes de una demo o de pasar a producción).

```bash
rm llaves/privada.pem llaves/publica.pem
openssl genrsa -out llaves/privada.pem 2048
openssl rsa -in llaves/privada.pem -pubout -out llaves/publica.pem
docker compose restart api
```

Efecto: **todos los tokens emitidos con la llave anterior dejan de ser válidos** y cada persona tiene que volver a iniciar sesión. Si otros servicios tenían la pública anterior, hay que entregarles la nueva.

---

## Alternativa sin OpenSSL

Si no puedes usar OpenSSL, genera el par con Python dentro del contenedor (requiere que `cryptography` ya esté en `requirements.txt` y la imagen reconstruida):

```bash
docker compose run --rm api python -c "
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
Path('llaves/privada.pem').write_bytes(llave.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
))
Path('llaves/publica.pem').write_bytes(llave.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
))
print('Llaves generadas en llaves/')
"
```

El resultado es equivalente al de OpenSSL.

---

## Problemas comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `FileNotFoundError: .../llaves/privada.pem` al arrancar | No has generado las llaves | Sigue [Generar las llaves](#generar-las-llaves) |
| `Algorithm 'RS256' could not be found. Do you have cryptography installed?` | Falta `cryptography` o la imagen no se reconstruyó | Revisa `requirements.txt` y corre `docker compose build` |
| `Could not deserialize key data` | El archivo está vacío, incompleto o no es una llave PEM | Bórralo y genera el par de nuevo |
| `token_invalido` con un token recién creado | El token se firmó con otro par de llaves (otra máquina, o rotaste) | Inicia sesión de nuevo para obtener uno firmado con tus llaves |
| `git status` muestra un `.pem` | La llave está fuera de `llaves/` o falta la regla en `.gitignore` | Muévela a `llaves/` y revisa con `git check-ignore -v` |
| `openssl: command not found` (Windows) | Estás en PowerShell o CMD | Usa Git Bash o la [alternativa sin OpenSSL](#alternativa-sin-openssl) |

---
