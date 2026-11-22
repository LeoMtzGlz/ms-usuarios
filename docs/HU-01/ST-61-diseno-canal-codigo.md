# HU-01 · Diseño: avisar por qué canal sale el código (ST-61)

**Historia:** HU-01 · Elegir por dónde recibo mis códigos
**Subtarea:** ST-61 · [Backend] Resolver el canal al pedir un código
**Responsable:** Santiago Mora (santiago-amn)
**Estado:** aprobado el 2026-11-22.

## Para qué

HU-01 pide que cada solicitud de código pueda indicar el canal (correo o WhatsApp), que si no se indica se use el preferido y que, si el canal elegido no está disponible, se use el correo **y la respuesta lo diga**. `elegir_canal(usuario, canal=None)` (HU-03 / ST-71) ya resuelve el canal y cambia a correo, pero en silencio: quien llama no se entera.

## Objetivos

- La respuesta del registro dice por qué canal salió el código (`canal_codigo`) y si ese canal es distinto del pedido (`canal_sustituido`).
- Las demás respuestas que pidan un código (reenvío, ST-75) usan la misma comparación cuando existan.

## Fuera de alcance

- El serializer de perfil con `canal_preferido` (ST-60): depende del endpoint de perfil de ST-163, de José de Jesús Téllez.
- Las pruebas completas de HU-01 (ST-62, de Daniel Gómez).
- La recuperación de contraseña (HU-10): responde siempre lo mismo para no revelar si la cuenta existe; avisar ahí del cambio de canal filtraría esa información.
- Comprobar que el proveedor de WhatsApp esté configurado o responda: un fallo de envío lo cubre el respaldo a correo de T-10.
- Cambiar la firma de `elegir_canal`, `crear_codigo` o `generar_codigo`, que usan las PRs de activación (#66) y recuperación (#79).

## Qué sería un fracaso aunque funcione

- Que la respuesta marque «sustituido» cuando el canal no cambió, o que no lo marque cuando sí cambió.
- Que la respuesta exponga el código o cualquier dato sensible.
- Que se rompa un llamador existente de `generar_codigo()`.

## Restricciones

- Sin migraciones y sin tocar `usuarios/models.py` ni `config/`.
- `elegir_canal`, `crear_codigo` y `generar_codigo` conservan su firma.

## Enfoques considerados

| Enfoque | Qué cambia | Por qué sí o no |
| --- | --- | --- |
| **A. El endpoint compara** `registro.canal` con el canal pedido | Solo la vista; ninguna firma | **Elegido.** `generar_codigo()` ya devuelve el registro con el canal realmente usado. Sin riesgo para las otras PRs |
| B. `elegir_canal` devuelve un objeto con `canal` y `sustituido` | Cambia el tipo de retorno y a sus llamadores | Más explícito, pero toca `usuarios/codigos.py`, donde también escribe la PR #66 |

## Decisiones

- **«No disponible» = WhatsApp sin teléfono** (lo que `elegir_canal` ya hace). No se revisa el proveedor ni se exige teléfono *verificado*: el propio código de activación verifica el teléfono.
- **Dos campos nuevos en el 201 del registro:** `canal_codigo` (`correo` o `whatsapp`) y `canal_sustituido` (booleano). Son campos de la respuesta, no del cuerpo de la petición.
- **El canal pedido en el registro es `canal_preferido`**, porque el registro no recibe otro canal.

## Lo que queda al implementador

- Los nombres de las pruebas y su organización, mientras cubran lo del plan.
- El texto de la documentación y su estilo, siguiendo `docs/HU-03/ST-71-generar-codigo.md`.
