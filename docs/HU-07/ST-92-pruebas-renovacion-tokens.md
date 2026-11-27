
# HU-07 — Renovar mi sesión sin volver a iniciar sesión

## ST-92. Pruebas de renovación de tokens

**Estado:** En desarrollo

### 1. Descripción

Se implementaron pruebas automatizadas adicionales para verificar el comportamiento del endpoint de renovación de tokens JWT.

Las pruebas complementan la cobertura funcional y de seguridad desarrollada previamente en ST-90, evitando modificar la lógica del serializer y del endpoint.

### 2. Endpoint evaluado

- **Método:** `POST`
- **Ruta:** `/api/v1/auth/token/renovar/`
- **Implementación:** `CustomTokenRefreshSerializer` y `CustomTokenRefreshView`.

### 3. Escenarios de prueba

| Escenario | Resultado esperado |
|---|---|
| Refresh token vencido | HTTP 401 y sin nuevos tokens |
| Access token enviado como refresh | HTTP 401 y sin nuevos tokens |
| Solicitud sin campo `refresh` | HTTP 400 |
| Refresh token revocado explícitamente | HTTP 401 y sin nuevos tokens |
| Duración del nuevo access token | 15 minutos |
| Renovaciones consecutivas | Rotación correcta e invalidación de tokens anteriores |

### 4. Implementación de las pruebas

Se agregó el archivo:

`usuarios/tests/test_refresh.py`

Las pruebas utilizan:

- `pytest` y `pytest-django`.
- `APIClient` mediante el fixture `api_client`.
- El fixture `usuario` para utilizar usuarios de prueba.
- El fixture `llaves` para utilizar claves JWT temporales.
- `CustomTokenObtainPairSerializer.get_token()` para generar tokens con los claims personalizados del proyecto.
- `RefreshToken` y `AccessToken` de SimpleJWT.

Las pruebas negativas verifican las respuestas HTTP y confirman que no se entregan tokens cuando una renovación es rechazada.

### 5. Pruebas realizadas

**Pruebas específicas:**

```bash
python -m pytest usuarios/tests/test_refresh.py -v
```

Resultado: **6 passed**.

**Suite general:**

```bash
python -m pytest -q
```

Resultado: **803 passed, 2 xfailed**.

Los dos `xfail` corresponden a pruebas existentes y no representan fallos inesperados introducidos por ST-92.

### 6. Verificaciones adicionales

Se realizaron las siguientes verificaciones:

```bash
python -m ruff check usuarios/tests/test_refresh.py
python manage.py check
python manage.py makemigrations --check --dry-run
```

Las verificaciones finalizaron sin errores.

### 7. Archivos agregados

- `usuarios/tests/test_refresh.py`
- `docs/HU-07/ST-92-pruebas-renovacion-tokens.md`

### 8. Resultado

Se ampliaron las pruebas automatizadas de la renovación de JWT con seis escenarios adicionales.

La implementación de ST-92 complementa ST-90 y verifica la expiración, revocación, validación de solicitudes, duración del access token y rotación consecutiva de refresh tokens.

No fue necesario modificar el código de producción del serializer ni del endpoint.
