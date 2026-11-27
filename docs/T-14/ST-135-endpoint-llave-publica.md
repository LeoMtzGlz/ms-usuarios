# ST-135 - Endpoint de llave pública

## Objetivo

Publicar la llave usada para verificar los JWT de `svc-usuarios` sin exponer material privado ni obligar a otros
microservicios a consultar esta base de datos.

## Contrato

- Método y ruta: `GET /api/v1/auth/llave-publica/`.
- Acceso: público mediante `AllowAny`; no procesa encabezados de autenticación.
- Formato: JWKS con una llave RSA para firma `RS256`.
- Caché: pública durante una hora mediante `Cache-Control: public, max-age=3600`.
- Error de configuración: `503 llave_publica_no_configurada`.

La respuesta contiene únicamente `kty`, `use`, `alg`, `kid`, `n` y `e`. Los parámetros privados de RSA nunca se
incluyen. El `kid` es la huella SHA-256 de la representación DER de la llave pública, codificada en base64url, por lo
que permanece estable mientras la llave no cambie.

## Ejemplo de respuesta

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "kid": "identificador-estable",
      "n": "modulo-rsa-en-base64url",
      "e": "AQAB"
    }
  ]
}
```

## Seguridad

El endpoint toma exclusivamente `SIMPLE_JWT["VERIFYING_KEY"]`. No lee ni transforma la llave privada. Si la llave
pública falta, es inválida o no es RSA, responde un error controlado y no devuelve detalles de la configuración.

La respuesta no se almacena en la caché interna de Django. De esta forma, el endpoint funciona en una instalación
recién migrada aunque todavía no exista la tabla de `DatabaseCache`; el navegador, gateway o proxy puede respetar el
encabezado público de una hora sin que este microservicio dependa de `cache_table`.
