# T-14 / ST-136 · Guía de integración para otros servicios

**Subtarea:** ID 136 · [Documentación] Escribir la guía de integración para otros servicios
**Tarea padre:** T-14 · Publicar la llave pública para los demás microservicios
**Autora:** Isamar Chávez Díaz (chamar29)

Esta guía es para los equipos de **catálogo, pedidos u otros microservicios** que necesitan saber
quién hace cada petición. Esos servicios **no consultan la base de svc-usuarios**: validan el token
JWT con la **llave pública** y leen el id y el rol directamente del token.

## Cómo funciona

```text
Cliente ── POST login ──▶ svc-usuarios   (firma el token con la llave PRIVADA)
Cliente ◀── access token ─┘
Cliente ── GET /api/... + "Authorization: Bearer <token>" ──▶ otro servicio
                                    (verifica la firma con la llave PÚBLICA, sin llamar a svc-usuarios)
```

| Dato del token | Claim | Ejemplo | Quién lo agrega |
| --- | --- | --- | --- |
| Id del usuario | `user_id` | `"8f1c...-uuid"` | T-04 (ya está) |
| Emisor | `iss` | `"svc-usuarios"` | T-04 (ya está) |
| Tipo | `token_type` | `"access"` | SimpleJWT |
| Vencimiento | `exp` | 15 minutos después de `iat` | T-04 (ya está) |
| Rol | `rol` | `"cliente"`, `"operativo"` o `"administrador"` | HU-05 (login), pendiente |

## 1. Instalar SimpleJWT en el otro servicio

En su `requirements.txt` (las mismas versiones que svc-usuarios):

```text
djangorestframework-simplejwt==5.5.1
cryptography==50.0.1
```

## 2. Obtener la llave pública

Solo se necesita la **pública** (`publica.pem`). La privada **nunca** sale de svc-usuarios.

- **Hoy:** copiar `llaves/publica.pem` de svc-usuarios (se genera como dice `docs/llaves_rs256_sjwt.md`).
- **Cuando se fusione la ST-135:** se podrá descargar de `GET /api/v1/auth/llave-publica/` (formato JWKS).
  Mientras tanto, usa el archivo `publica.pem` (ver la nota de `JWK_URL` en el paso 3).

## 3. Configurar el otro servicio (solo con `VERIFYING_KEY`)

En su `settings.py`:

```python
from pathlib import Path

SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    # Solo la llave PÚBLICA: este servicio verifica tokens, nunca los firma
    "VERIFYING_KEY": Path(BASE_DIR / "llaves" / "publica.pem").read_text(),
    "ISSUER": "svc-usuarios",          # rechaza tokens que no emitió svc-usuarios
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Clase propia (abajo): stateless + rechaza con 401 los tokens sin rol
        "comun.autenticacion.JWTDeUsuarios",
    ),
}
```

Y la clase, por ejemplo en `comun/autenticacion.py` del otro servicio:

```python
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class JWTDeUsuarios(JWTStatelessUserAuthentication):
    """Valida el token de svc-usuarios sin consultar su base y exige el claim rol."""

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if not token.get("rol"):
            raise InvalidToken("El token no trae rol.")
        return token
```

> **¿Por qué una clase propia?** Con `JWTStatelessUserAuthentication` sola, un token sin `rol`
> pasa como autenticado (con `rol = None`), y el criterio de T-14 pide que se rechace con 401.
> `JWTDeUsuarios` hace la misma validación de firma, emisor y vencimiento, y además exige el rol.

> **¿Por qué `JWTStatelessUserAuthentication` y no `JWTAuthentication`?**
> `JWTAuthentication` busca al usuario en la tabla de usuarios, y el otro servicio no tiene esa tabla.
> La versión *stateless* confía en la firma y crea un `TokenUser` con los claims del token.

> **`JWK_URL` (descargar la llave del endpoint): pendiente de la ST-135.** SimpleJWT 5.5.1 firma
> los tokens sin `kid` en el encabezado, y el cliente JWKS busca la llave por `kid`, así que esa
> opción falla con *"Unable to find a signing key that matches: None"*. Por ahora usa
> `VERIFYING_KEY` con el archivo `publica.pem`.

## 4. Leer el id y el rol en una vista

```python
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class EsAdministrador(BasePermission):
    """Solo deja pasar tokens con rol administrador."""

    def has_permission(self, request, view):
        return bool(request.auth) and request.auth.get("rol") == "administrador"


class MisPedidosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario_id = str(request.user.id)    # claim user_id
        rol = request.auth.get("rol")        # claim rol (llega con HU-05)
        return Response({"usuario": usuario_id, "rol": rol})
```

- `request.user` es un `TokenUser`: `request.user.id` es el `user_id` del token.
- `request.auth` es el token ya validado: `request.auth.get("rol")` devuelve el rol.
- Los valores del rol son los de `comun/roles.py`: `administrador`, `cliente` y `operativo`.

## 5. Qué se rechaza con 401

| Caso | Resultado |
| --- | --- |
| Sin encabezado `Authorization` en una vista con `IsAuthenticated` | 401 |
| Token firmado con **otra llave** | 401 |
| Token **vencido** (más de 15 minutos) | 401 |
| Token de otro emisor (`iss` distinto de `svc-usuarios`) | 401 |
| Token **sin `rol`** | 401 (lo rechaza `JWTDeUsuarios`) |

> **Ojo con las cuentas desactivadas.** Como el otro servicio no consulta la base de svc-usuarios,
> un token de una cuenta que se desactivó **sigue siendo válido allá hasta que vence (máximo 15
> minutos)**. Es el costo de no hacer una consulta por petición.

## 6. Probarlo a mano

```powershell
# 1. Pedir el token a svc-usuarios (cuando exista el login de HU-05)
# 2. Llamar al otro servicio con el token:
curl -H "Authorization: Bearer <access_token>" http://localhost:8001/api/mis-pedidos/
```

## Verificación

La configuración del paso 3 y la vista del paso 4 se probaron con un token RS256 firmado con una
llave privada y verificado solo con la pública: un token válido responde 200 con `id` y `rol`; uno
firmado con otra llave, vencido o sin `rol` responde 401. Las pruebas automáticas quedan en la **ST-137**.

## Pendientes que dependen de otras subtareas

- **ST-135:** endpoint `GET /api/v1/auth/llave-publica/` (JWKS). Para usar `JWK_URL` los tokens
  tendrían que llevar `kid` en el encabezado.
- **HU-05:** que el login agregue el claim `rol` al token.