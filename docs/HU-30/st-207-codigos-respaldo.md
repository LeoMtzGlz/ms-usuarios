# HU-30 — Activar la verificación en dos pasos (2FA)

## ST-207 : Generar los códigos de respaldo

**Estado:** Terminada. En revisión (PR ```t-30/st-207 Generar los códigos de respaldo```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Al confirmar el 2FA se entregan 10 códigos de respaldo una sola vez. Se guardan con hash.

### Resultado:
- `usuarios/models.py` : modelo ```CodigoRespaldo``` (```usuario```, ```codigo_hash```, ```usado_en```, ```creado_en```); migración ```usuarios/<0006>_codigo_respaldo```.
- ```usuarios/dos_factores.py```:
  - ```generar_codigos_respaldo(usuario)``` → borra los anteriores, crea 10 códigos nuevos con formato ```XXX-XXX``` (con ```secrets``` y sin caracteres confusos: 0/O, 1/I/L) y guarda solo su hash con ```make_password``` (Argon2). Devuelve los códigos en claro: es la única vez que existen así.
  - ```usar_codigo_respaldo(usuario, codigo)``` → valida y marca como usado un código (un solo uso). Acepta minúsculas y sin guion. La usará HU-31 (st-210 / st-211).
- ```usuarios/views_2fa.py```, en ```Confirmar2FAView```: cuando el primer código TOTP es correcto, se generan los códigos dentro de la misma transacción y la respuesta agrega ```codigos_respaldo```:

> Respuesta del endpoint :  
    `{"confirmado": true, "mensaje": "Verificación en dos pasos activada.", "codigos_respaldo": ["ABC-EFH", ...]}`

### Decisiones:
- Regenerar borra los anteriores: solo hay un juego válido a la vez.
-Los códigos nunca van a la bitácora ni a los logs; ```registrar_evento("2fa_activado", ...)``` no los recibe.
- ```CodigoRespaldo``` no se registra en el admin de Django.
- Verificar un código puede hacer hasta 10 comprobaciones Argon2; es aceptable para un uso esporádico.

### Pruebas:
> Corre:  
    `docker compose run --rm api pytest usuarios/tests/test_codigos_respaldo.py` (6 passed)
- ```test_genera_10_unicos_con_formato``` → 10 códigos distintos con formato ```XXX-XXX```.
- ```test_se_guardan_con_hash``` → la base no contiene ningún código en claro y ```check_password``` los reconoce.
- ```test_regenerar_invalida_los_anteriores``` → solo queda el juego nuevo.
- ```test_un_solo_uso``` → el mismo código no sirve dos veces.
- ```test_acepta_minusculas_y_sin_guion```.
- ```test_no_sirve_para_otro_usuario```.