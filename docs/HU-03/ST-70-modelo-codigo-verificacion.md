# ST-70 · Modelo CodigoVerificacion

**Historia:** HU-03 · Activar mi cuenta con un código
**Subtarea:** ST-70 · [Backend] Crear el modelo CodigoVerificacion
**Autor:** Juan Diego Lomelí Coyazo (DiegoLC04) · **Revisora:** Katia Victoria (KPVE2004)

## Qué es y para qué sirve

Cuando una persona se registra, recibe por correo o WhatsApp un código de 6 dígitos que debe escribir para activar su cuenta. Este modelo guarda cada código que genera el sistema, para poder comprobarlo después.

Es el mismo modelo para tres usos: activar la cuenta, recuperar la contraseña (HU-10) y cambiar el correo o el teléfono. Lo único que cambia entre ellos es el campo `proposito`.

## Qué se hizo

- En `usuarios/models.py`: la lista `Proposito` y el modelo `CodigoVerificacion`.
- La migración `usuarios/migrations/0003_codigoverificacion.py`.

## Campos

| Campo | Tipo | Para qué sirve |
| --- | --- | --- |
| `usuario` | Clave foránea a `Usuario` | A quién pertenece el código |
| `proposito` | Texto (`Proposito`) | `activacion`, `recuperacion` o `cambio_contacto` |
| `canal` | Texto (`Canal`) | Por dónde se envió: `correo` o `whatsapp` |
| `codigo_hash` | Texto de hasta 128 caracteres | El código guardado con hash, nunca en claro |
| `creado_en` | Fecha y hora | Se llena sola al crear el registro |
| `expira_en` | Fecha y hora | Hasta cuándo sirve el código |
| `usado` | Booleano | Si ya se usó o se anuló |
| `intentos` | Entero pequeño | Cuántos intentos fallidos lleva |

## Decisiones

- **Solo se guarda el hash.** No existe ninguna columna con el código en claro. Si alguien leyera la base de datos, no podría usar los códigos.
- **Una lista para el propósito.** `Proposito` evita escribir textos sueltos y permite reutilizar el modelo en otras historias.
- **Reutiliza `Canal`.** Usa la misma lista de canales que `Usuario`, para no repetir opciones.
- **Índice por usuario, propósito y uso.** La consulta más común es "el código pendiente de este usuario para este propósito", y el índice la acelera.
- **`on_delete=CASCADE`.** Si se borra a la persona, se borran sus códigos.
- **`usado` e `intentos`.** Permiten que un código no se use dos veces y que se anule tras 5 intentos fallidos.

## Qué no hace

Este modelo solo guarda datos. Lo demás de HU-03 queda para otras subtareas:

- ST-71: generar el código, calcular su hash y encolar el envío.
- ST-72: el endpoint que valida el código.
- ST-73: las pruebas de activación.

## Cómo comprobarlo

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py shell
```

Dentro del shell:

```python
from usuarios.models import CodigoVerificacion
CodigoVerificacion.objects.count()   # debe responder 0
```

Y las pruebas del proyecto:

```bash
docker compose exec api pytest -q
```