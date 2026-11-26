
# HU-07 — Renovar mi sesión sin volver a iniciar sesión

## ST-91. Programar la limpieza de tokens vencidos

**Estado:** En desarrollo

### 1. Descripción

Se implementó un mecanismo de limpieza periódica para eliminar los registros de tokens JWT vencidos de la base de datos.

La implementación utiliza el comando `flushexpiredtokens` de SimpleJWT, ejecutado por un servicio independiente de Docker Compose.

### 2. Implementación

Se agregó el servicio `token_cleanup` en `docker-compose.yml`.

Este servicio:

- Utiliza la imagen del microservicio Django.
- Se conecta a PostgreSQL mediante `db:5432`.
- Espera a que la base de datos esté saludable.
- Ejecuta el comando `python manage.py flushexpiredtokens`.
- Repite la limpieza aproximadamente cada 24 horas.
- Registra en los logs el inicio y el resultado de cada ejecución.
- Se reinicia automáticamente mediante `restart: unless-stopped` si su proceso principal termina inesperadamente.

No fue necesario modificar la lógica de autenticación ni agregar dependencias.

### 3. Funcionamiento

El proceso ejecuta una primera limpieza cuando inicia el servicio.

Posteriormente, espera 86,400 segundos antes de realizar la siguiente ejecución.

La limpieza elimina registros vencidos de:

- `OutstandingToken`.
- `BlacklistedToken`, cuando están asociados a tokens vencidos.

Los tokens vigentes y sus registros permanecen almacenados.

La programación utiliza un intervalo relativo al inicio del servicio y no una hora fija del día.

### 4. Manejo de errores

El servicio registra en los logs si la limpieza finaliza correctamente o presenta un error.

Si una ejecución falla, el ciclo continúa y se realiza un nuevo intento después del intervalo configurado.

Este mecanismo no implementa reintentos inmediatos ni alertas automáticas; dichas capacidades podrían incorporarse si los requisitos operativos lo exigen.

### 5. Pruebas realizadas

**Validación de Docker Compose:**

```bash
docker compose config --quiet
```

**Inicio del servicio:**

```bash
docker compose up -d --force-recreate token_cleanup
```

**Verificación de estado:**

```bash
docker compose ps token_cleanup
```

**Revisión de logs:**

```bash
docker compose logs --tail=15 token_cleanup
```

**Ejecución manual del comando:**

```bash
docker compose exec token_cleanup python manage.py flushexpiredtokens
```

**Prueba automatizada:**

```bash
python -m pytest usuarios/tests/test_limpieza_tokens.py -v
```

Resultado: **1 prueba aprobada**.

La prueba verifica que:

1. Los registros de tokens vencidos se eliminan.
2. Los registros asociados de la lista negra se eliminan.
3. Los tokens vigentes permanecen almacenados.
4. Los registros vigentes de la lista negra se conservan.

**Verificación de estilo:**

```bash
python -m ruff check usuarios/tests/test_limpieza_tokens.py
```

Resultado: `All checks passed!`

### 6. Archivos modificados

- `docker-compose.yml`
- `usuarios/tests/test_limpieza_tokens.py`
- `docs/HU-07/ST-91-limpieza-tokens-vencidos.md`

### 7. Consideraciones

- El servicio debe mantenerse activo para ejecutar las limpiezas periódicas.
- La programación se realiza aproximadamente cada 24 horas.
- El proceso es independiente del servicio `api` y del trabajador de notificaciones.
- La limpieza actúa sobre registros vencidos y no invalida los tokens vigentes.
- La prueba automatizada verifica la limpieza, mientras que la ejecución periódica se valida mediante la configuración y los logs del servicio.

### 8. Resultado

Se implementó y probó el mecanismo de limpieza de tokens JWT vencidos mediante un servicio independiente de Docker Compose.

La automatización permite ejecutar el comando de mantenimiento periódicamente sin intervención manual.

**Responsable:** ST-91 — HU-07.
