# T-14 / ST-137 · Pruebas de validación en otros servicios

**Subtarea:** ID 137 · [Pruebas] Pruebas
**Tarea padre:** T-14 · Publicar la llave pública para los demás microservicios
**Responsable:** Isamar Chávez Díaz (chamar29)
**Estado:** En revisión

## Descripción

Pruebas automáticas de lo que explica la guía de la ST-136
(`docs/T-14/ST-136-guia-integracion.md`): un microservicio externo valida los tokens de
svc-usuarios **solo con la llave pública**, sin consultar su base, con la clase `JWTDeUsuarios`
(`JWTStatelessUserAuthentication` + exige el claim `rol`).

Archivo: `usuarios/tests/test_validacion_otros_servicios.py`. Usa el fixture compartido `llaves`
de `conftest.py` (par RS256 temporal), así que no necesita `llaves/*.pem`.

## Casos que se prueban

| Prueba | Caso | Esperado |
| --- | --- | --- |
| `test_token_valido_entrega_id_y_rol` | Token válido con rol | 200 con `id` y `rol` |
| `test_token_firmado_con_otra_llave_responde_401` | Firmado con **otra llave** | 401 `token_invalido` |
| `test_token_vencido_responde_401` | Token **vencido** | 401 `token_invalido` |
| `test_token_sin_rol_responde_401` | Token **sin rol** | 401 `token_invalido` |
| `test_token_de_otro_emisor_responde_401` | `iss` distinto de `svc-usuarios` | 401 |
| `test_token_de_renovacion_no_sirve_como_acceso` | Token de renovación usado como acceso | 401 |
| `test_sin_encabezado_responde_401` | Sin `Authorization` | 401 con `WWW-Authenticate: Bearer` |
| `test_token_real_de_svc_usuarios_se_valida_solo_con_la_llave_publica` | Token emitido por `RefreshToken.for_user` | 200 |

Cubre el criterio de T-14: *"Un token firmado con otra llave, vencido o sin rol se rechaza con 401"*.

## Cómo correrlas

```powershell
docker compose run --rm api pytest usuarios/tests/test_validacion_otros_servicios.py -v
```

## Resultado

8 pruebas en verde. `ruff check .` sin errores.

## Pendiente

- El claim `rol` lo agregará el login de HU-05; mientras tanto la última prueba lo agrega a mano.
- La ST-135 (endpoint de llave pública) no es necesaria para estas pruebas.