# ST-141 - Generar la contraseña temporal con `secrets`

## Objetivo

Cuando un administrador da de alta a un usuario operativo (HU-15), la cuenta necesita una contraseña con la que
entrar por primera vez. Esa contraseña la genera el sistema, no la escoge el administrador, y es temporal:
quien la recibe debe cambiarla al entrar.

El generador vive en `usuarios/contrasenas.py` y tiene una sola función pública.

## La función

```python
from usuarios.contrasenas import generar_contrasena_temporal

generar_contrasena_temporal()      # 'k7!Rm4xQe2Hz'  (12 caracteres)
generar_contrasena_temporal(16)    # longitud personalizada
generar_contrasena_temporal(7)     # ValueError: mínimo 8 caracteres
```

| Parámetro | Valor por defecto | Regla |
| --- | --- | --- |
| `longitud` | `LONGITUD_TEMPORAL = 12` | Mínimo `LONGITUD_MINIMA = 8`; menos lanza `ValueError` |

Devuelve un `str`. No guarda nada, no escribe en la bitácora y no depende de la base de datos.

## Cómo se genera

1. **Un carácter de cada grupo.** Se toma una mayúscula, una minúscula, un número y un símbolo, así que la contraseña
   siempre cumple `AUTH_PASSWORD_VALIDATORS` (T-12), incluido el validador propio de mayúscula y número.
2. **Relleno aleatorio.** Los caracteres que faltan para llegar a la longitud pedida salen de los cuatro grupos juntos.
3. **Barajado.** Sin este paso, los cuatro primeros caracteres siempre serían mayúscula, minúscula, número y símbolo,
   en ese orden, y cualquiera podría descartar combinaciones.

Todas las elecciones usan `secrets.choice` y el barajado usa `secrets.SystemRandom()`. Ambos leen del generador
criptográfico del sistema operativo. **No se usa el módulo `random`**: es predecible y no sirve para contraseñas.

## El alfabeto

| Grupo | Caracteres | Cantidad |
| --- | --- | --- |
| Mayúsculas | `A-Z` sin `I` ni `O` | 24 |
| Minúsculas | `a-z` sin `l` | 25 |
| Números | `2-9` (sin `0` ni `1`) | 8 |
| Símbolos | `! @ # $ % & * - _ + =` | 11 |
| **Total** | | **68** |

Se quitaron `O`, `0`, `I`, `l` y `1` porque la contraseña se la dicta o imprime una persona a otra, y esos
caracteres se confunden fácilmente. Los símbolos son solo los comunes del teclado: se evitan comillas, espacios y barras,
que suelen dar problemas al copiar, pegar o escribir en un formulario.

## Qué tan difícil es adivinarla

Con 12 caracteres y la regla de "al menos uno de cada grupo" hay unas 6.5 × 10²¹ contraseñas posibles, es decir,
unos **72.5 bits** de entropía (73.0 sin la regla). Es mucho más de lo que se puede probar por fuerza bruta contra
el login, que además se bloquea tras 5 intentos fallidos (django-axes).

## Dónde se usa

`POST /api/v1/usuarios/` (ST-140), en `usuarios/views_admin.py`:

```text
contrasena = generar_contrasena_temporal()
usuario = serializer.save(contrasena=contrasena)   # create_user guarda solo el hash Argon2
...
Response({..., "contrasena_temporal": contrasena})  # se devuelve una sola vez
```

Lo que pasa con la contraseña después de generarla:

| Destino | ¿Recibe la contraseña? |
| --- | --- |
| Base de datos | Solo su hash Argon2; el texto plano no se guarda |
| Respuesta del alta | Sí, **una sola vez**, con `Cache-Control: no-store` |
| Bitácora (`svc.auditoria`) | No. El evento `alta_usuario` registra quién creó a quién y el rol |
| Aviso por correo (ST-142) | No. Solo lleva instrucciones para iniciar sesión |

Si se pierde, no se puede recuperar: hay que generar una nueva (HU-19, `POST /usuarios/{id}/restablecer-password/`,
que reutiliza esta misma función).

## Qué obliga a cambiarla

La cuenta se crea con `debe_cambiar_password=True`. El login copia ese valor al token y el permiso
`ContrasenaDefinitiva` (ST-116) responde `403 debe_cambiar_password` en todos los endpoints que usan los permisos por
defecto. Al cambiar la contraseña, `Usuario.cambiar_password()` pone el indicador en `False` y cierra las sesiones
anteriores.

## Pruebas

`usuarios/tests/test_contrasenas.py`:

| Prueba | Qué garantiza |
| --- | --- |
| `test_tiene_doce_caracteres_por_defecto` | Longitud por defecto de 12 |
| `test_respeta_la_longitud_pedida` | Longitudes 8, 12 y 20 |
| `test_siempre_trae_mayuscula_minuscula_numero_y_simbolo` | 200 generaciones con los cuatro grupos |
| `test_no_usa_caracteres_ambiguos` | Ningún `O`, `0`, `I`, `l` ni `1` |
| `test_cumple_la_politica_de_contrasenas` | Pasa `validate_password` |
| `test_dos_llamadas_dan_contrasenas_distintas` | 100 contraseñas, ninguna repetida |
| `test_rechaza_longitudes_menores_a_ocho` | `ValueError` con menos de 8 |

Que la contraseña no llegue a la bitácora ni se guarde en texto plano lo prueba `usuarios/tests/test_alta_usuario.py`.

## Reglas para quien la use

- No guardar la contraseña ni escribirla en logs. Para eventos, `registrar_evento` ya oculta las claves que contienen
  `password` o `contrasena`, pero lo más seguro es no pasarla.
- No mandarla por correo ni por WhatsApp: se entrega solo en la respuesta del endpoint.
- No bajar `longitud` de 12 sin motivo; el mínimo de 8 existe solo para que la función no genere algo que la política
  rechazaría.
