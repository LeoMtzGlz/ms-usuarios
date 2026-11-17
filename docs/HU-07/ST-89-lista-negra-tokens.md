# HU-07 — Renovar la sesión sin volver a iniciar sesión

## ST-89. Activar la lista negra de SimpleJWT

**Estado:** Completada  
**Responsable:** l22420415

### 1. Descripción

Se activó la app `token_blacklist` de SimpleJWT y la rotación del token de renovación (*refresh*). Desde ahora, cada vez que un refresh se usa para renovar la sesión, SimpleJWT entrega un refresh **nuevo** y pone el anterior en **lista negra**, de modo que un refresh robado o ya usado no se puede volver a usar.

Esta subtarea solo deja lista la configuración. El endpoint de renovación es ST-90.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `config/settings.py` | `"rest_framework_simplejwt.token_blacklist"` en `INSTALLED_APPS` (debajo de `drf_spectacular`) |
| `config/settings.py` | `"ROTATE_REFRESH_TOKENS": True` y `"BLACKLIST_AFTER_ROTATION": True` en `SIMPLE_JWT` (debajo de `REFRESH_TOKEN_LIFETIME`) |
| `usuarios/tests/test_lista_negra.py` | Pruebas de la configuración, el registro, la rotación y la lista negra |

No se generaron migraciones propias: las tablas vienen con la librería y se crean con `migrate`.

### 3. Qué hacen la rotación y la lista negra

| Opción | Efecto |
|---|---|
| `token_blacklist` (app) | Cada refresh que se emite (`RefreshToken.for_user(...)`) se registra en la base con su `jti`, usuario y fecha de vencimiento. Permite invalidar un refresh antes de que venza |
| `ROTATE_REFRESH_TOKENS` | Al renovar, además del access nuevo se entrega un **refresh nuevo** |
| `BLACKLIST_AFTER_ROTATION` | Al rotar, el refresh que se usó queda en **lista negra**; si alguien lo vuelve a presentar, SimpleJWT lo rechaza (`Token is blacklisted`) |

Flujo de una renovación:

1. El cliente manda su refresh `R1`.
2. SimpleJWT verifica firma, vencimiento y que `R1` no esté en lista negra.
3. Pone `R1` en lista negra y emite `R2` (con `jti` nuevo), que queda registrado.
4. Responde `{"access": ..., "refresh": R2}`. Si `R1` se usa otra vez, falla.

Un refresh también se puede invalidar a mano con `RefreshToken(texto).blacklist()`; eso es lo que usará el cierre de sesión.

### 4. Tablas que se crean

| Modelo | Tabla | Qué guarda |
|---|---|---|
| `OutstandingToken` | `token_blacklist_outstandingtoken` | Todos los refresh emitidos: usuario, `jti`, token, creación y vencimiento |
| `BlacklistedToken` | `token_blacklist_blacklistedtoken` | Los refresh invalidados (relación uno a uno con `OutstandingToken`) y la fecha en que se invalidaron |

Se crean con:

```bash
docker compose run --rm api python manage.py migrate
```

**Verlas en el admin:** entrar a <http://localhost:8000/admin/> con un superusuario; aparece la sección **Token Blacklist** con *Outstanding tokens* y *Blacklisted tokens*. Las dos pantallas permiten buscar por usuario o `jti`; *Outstanding tokens* es de solo lectura (no se pueden crear ni editar tokens desde el admin). Para invalidar un refresh se usa `RefreshToken(texto).blacklist()` en código, no el admin.

Desde PostgreSQL:

```bash
docker compose exec db psql -U ms_user -d ms_usuarios -c "SELECT count(*) FROM token_blacklist_outstandingtoken;"
```

### 5. Cómo probarlo

```bash
docker compose run --rm api pytest usuarios/tests/test_lista_negra.py -v
```

Las pruebas firman con un par de llaves temporal (como `test_jwt_rs256.py`), así que no necesitan `llaves/privada.pem`. Cubren:

- La app está instalada y las dos opciones están activas.
- Emitir un refresh lo registra como `OutstandingToken`.
- Renovar con `TokenRefreshSerializer` entrega un refresh nuevo y el anterior queda en lista negra.
- Renovar otra vez con el refresh anterior falla.
- Un refresh puesto en lista negra a mano ya no sirve.

### 6. Qué sigue

| Subtarea | Qué hará |
|---|---|
| ST-90 | Serializer propio de renovación y su endpoint (la ruta la define ST-90) |
| ST-91 | Limpieza periódica de tokens vencidos (`python manage.py flushexpiredtokens`), porque `OutstandingToken` crece con cada login y cada renovación |
| ST-92 | Pruebas del endpoint de renovación y de la limpieza |

### 7. Nota para HU-06 ("recordarme")

Con `ROTATE_REFRESH_TOKENS`, el `TokenRefreshSerializer` de SimpleJWT llama a `refresh.set_exp()` sin argumentos al rotar, así que el refresh nuevo toma siempre `REFRESH_TOKEN_LIFETIME` global (**7 días**). Si el login emite un refresh de 1 día (sin "recordarme"), la primera renovación lo convertiría en uno de 7 días.

Por eso el serializer propio de ST-90 debe **conservar la duración original** del token: por ejemplo, guardar un claim `recordarme` al emitirlo y, al rotar, usar `refresh.set_exp(lifetime=...)` con la duración que corresponde a ese claim.

### 8. Resultado

La lista negra y la rotación del refresh quedaron activas: cada refresh emitido queda registrado, cada renovación entrega uno nuevo e invalida el anterior, y un refresh en lista negra ya no se puede usar.

**ST-89 finalizada.**

**Responsable de la actividad:** l22420415.
