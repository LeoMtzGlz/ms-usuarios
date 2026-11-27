# ST-238 – Definir el contrato genérico de integración y documentarlo en OpenAPI

**Estado:** En desarrollo
**Responsable:** Daniel Gómez Villaseñor (gomez-d)
**Subtarea:** ST-238

## Descripción

Se definirá el contrato genérico que permitirá vincular una cuenta de `ms-usuarios` con un registro administrado por otro microservicio.

La vinculación se solicitará durante el alta de usuarios mediante el endpoint `POST /api/v1/usuarios/`. El diseño deberá mantener a `ms-usuarios` independiente de las entidades y reglas de negocio de los servicios consumidores, permitiendo reutilizar la integración en distintos proyectos.

Cuando no se proporcione información de vinculación, el alta conservará su comportamiento actual.

## Contrato de integración

La petición al endpoint de alta incluirá un objeto opcional `vinculacion`:

```json
{
  "vinculacion": {
    "tipo_entidad": "chofer",
    "entidad_id": "uuid-de-la-entidad"
  }
}
```

- `tipo_entidad`: identificador genérico del tipo de registro que se desea vincular.
- `entidad_id`: UUID del registro administrado por el servicio externo.
- `vinculacion`: objeto opcional; su omisión no modifica el flujo actual de alta.

El cliente no proporcionará la URL ni seleccionará directamente el servicio externo. La dirección se configurará del lado de `ms-usuarios`.

El adaptador de integración enviará al servicio externo la siguiente estructura:

```json
{
  "user_id": "uuid-del-usuario",
  "entidad": {
    "tipo": "chofer",
    "id": "uuid-de-la-entidad"
  }
}
```

El servicio externo almacenará el `user_id` como referencia, sin establecer una llave foránea hacia la base de datos de `ms-usuarios`.

## Implementación

- Se documentará el objeto opcional `vinculacion` en el esquema de petición de `POST /api/v1/usuarios/`.
- Se definirán esquemas reutilizables de OpenAPI para la información de vinculación, la entidad externa y las respuestas de error, reutilizando el esquema común del proyecto cuando corresponda.
- Se agregarán ejemplos de petición con y sin vinculación.
- Se documentará el formato estándar de errores `{codigo, mensaje, campos}`.
- Se contemplarán los errores de datos inválidos, entidad inexistente, entidad ya vinculada y servicio externo no disponible.
- Se conservarán los permisos y mecanismos de autenticación existentes para el endpoint de alta.
- Se documentará que la comunicación con el servicio externo requiere un timeout y que su implementación corresponde a ST-237.
- Se distinguirá la autenticación del cliente frente a `ms-usuarios` de la autenticación entre microservicios.
- Se dejarán identificados los detalles pendientes de confirmación: ruta externa, respuesta exitosa, mecanismo de autenticación entre servicios, timeout exacto y comportamiento de idempotencia.

Los estatus HTTP considerados para la integración son `200`, `400`, `404`, `409` y `503`, sujetos a confirmación con la implementación del servicio externo. De igual manera, los códigos específicos de error documentados serán considerados propuestas hasta que se implementen y confirmen.

## Resultado

Se contará con un contrato genérico documentado en OpenAPI para solicitar la vinculación de una cuenta de `ms-usuarios` con una entidad administrada por otro microservicio.

La documentación permitirá identificar claramente los datos que recibe `ms-usuarios`, la estructura que enviará el adaptador al servicio externo, los errores contemplados y las condiciones de seguridad y disponibilidad de la integración.

El alcance de esta subtarea no incluye implementar la comunicación HTTP ni las validaciones contra el servicio externo, correspondientes a ST-237. Tampoco incluye las pruebas con el servicio simulado, correspondientes a ST-239.

## Validaciones

- `ruff check .`: pendiente.
- `python manage.py makemigrations --check --dry-run`: pendiente.
- `python manage.py migrate`: pendiente.
- `pytest`: pendiente.
- `git diff --check`: pendiente.
- Generación y revisión del esquema OpenAPI: pendiente.
