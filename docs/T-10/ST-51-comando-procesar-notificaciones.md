# T-10 — Procesar la bandeja de salida con reintentos y respaldo de canal

## ST-51. Crear el comando procesar_notificaciones

**Estado:** En revisión  
**Responsable:** l22420429 (David Melgoza · D3vo1)  
**Revisa:** Santiago Mora (santiago-amn), continúa con ST-52

### 1. Descripción

Se creó el comando `python manage.py procesar_notificaciones`, el worker que vacía la bandeja de salida
(tabla `Notificacion` de T-07). Cada 5 segundos toma hasta 20 notificaciones pendientes, las más viejas
primero, las envía por su canal y guarda el resultado. Sin Redis ni Celery: la cola es la tabla de PostgreSQL.

Las filas se toman con `select_for_update(skip_locked=True)`: si hay dos workers corriendo, cada uno se
salta lo que el otro ya bloqueó y nunca envían la misma notificación.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `notificaciones/worker.py` | Lógica del worker: tomar el lote, armar el mensaje, enviar, marcar enviada o fallida |
| `notificaciones/management/commands/procesar_notificaciones.py` | Comando con el bucle de 5 s y las opciones `--una-vez`, `--intervalo`, `--lote` |
| `notificaciones/management/__init__.py`, `.../commands/__init__.py` | Paquetes vacíos que Django necesita para encontrar el comando |
| `notificaciones/tests/test_worker.py` | 11 pruebas del worker y del comando |

No toca `settings.py`, `requirements.txt`, `.env.example` ni migraciones.

### 3. Cómo usarlo

```bash
docker compose run --rm api python manage.py procesar_notificaciones            # bucle cada 5 s
docker compose run --rm api python manage.py procesar_notificaciones --una-vez  # un lote y termina
```

`docker compose stop` (SIGTERM) o Ctrl+C terminan el lote en curso y detienen el worker sin cortar un envío
a la mitad. El servicio `worker` del `docker-compose.yml` es de ST-53.

### 4. Qué hace con cada notificación

1. **`antes_de_enviar()`**: hoy siempre deja pasar. Aquí entra el límite diario por canal de **ST-57**.
   Si devuelve `False`, la notificación sigue pendiente para el siguiente ciclo.
2. **`armar_mensaje()`**: renderiza `notificaciones/<plantilla>.txt` con el `contexto`.
3. **Envía** con `canal.enviar(destino, asunto, texto)`: al correo del usuario, o a su teléfono si el
   canal es WhatsApp.
4. **Si sale bien** (`marcar_enviada()`): estado `enviada` y el `contexto` se vacía, porque lleva el
   código (regla de T-07).
5. **Si falla** (`manejar_fallo()`): estado `fallida` y el error en `error`, con el código tapado por `***`.
   **ST-52** cambia esta función para sumar `intentos`, reintentar hasta 3 veces y crear la copia por correo.

Cada envío corre en su propio savepoint: si una notificación falla, el resto del lote sigue.

### 5. Dependencias

| Pieza | Subtarea | Estado al abrir este PR |
|---|---|---|
| Modelo `Notificacion` | T-07/ST-34 | En `development` |
| Interfaz `Canal` y función para elegir el canal | T-07/ST-35 | Pendiente: el worker la busca en `notificaciones.canales.obtener_canal` (confirmar nombre) |
| Canal de consola | T-07/ST-36 | Pendiente |
| CanalCorreo / CanalWhatsApp | T-08/ST-41, T-09/ST-48 | Pendientes |

Si falta la función de canales, el comando se detiene con un mensaje claro en lugar de marcar todo como fallido.
Las pruebas no dependen de ella: usan un canal falso.

### 6. Pruebas

```bash
docker compose run --rm api pytest notificaciones/tests/test_worker.py
```

| Prueba | Qué comprueba |
|---|---|
| `test_pendiente_pasa_a_enviada_y_se_vacia_el_codigo` | Pendiente → enviada; contexto vacío |
| `test_whatsapp_se_envia_al_telefono` | WhatsApp usa el teléfono, no el correo |
| `test_procesa_en_lotes_de_20_las_mas_viejas_primero` | De 25 pendientes envía 20 y deja las 5 más nuevas |
| `test_no_toma_enviadas_ni_fallidas` | Solo procesa pendientes |
| `test_si_el_canal_falla_queda_fallida_sin_el_codigo` | Fallo → fallida; el error no muestra el código |
| `test_un_fallo_no_detiene_el_resto_del_lote` | Una plantilla rota no frena a las demás |
| `test_antes_de_enviar_puede_posponer` | El punto de ST-57 puede dejarla pendiente |
| `test_dos_workers_no_envian_la_misma` | Con la fila bloqueada por otro worker, este se la salta |
| `test_comando_una_vez` | `--una-vez` procesa un lote |
| `test_bucle_espera_5_s_y_se_detiene_con_sigterm` | Espera 5 s entre lotes de 20 y se detiene con SIGTERM |
| `test_comando_avisa_si_faltan_los_canales` | Error claro si ST-35 no está |

### 7. Pendiente de confirmar

- Nombre de la función que entrega el canal (`notificaciones.canales.obtener_canal`) — l22420438 (ST-35).
- Si la plantilla la renderiza el worker o el canal (ST-41 dice que CanalCorreo usa `render_to_string`) — l22420438, l22420450.
- Qué subtarea revisa que el código no haya vencido antes de enviar (criterio de T-10; ST-54 lo prueba) — l22420391.
- Vaciar el `contexto` al enviar como forma de cumplir la regla de T-07 — l22420438.

### 8. Resultado

ruff, `makemigrations --check` y pytest pasan sobre PostgreSQL 16 y Python 3.12.
