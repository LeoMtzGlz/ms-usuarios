# ST-230 — Modelo `PerfilOperativo` (HU-36)

## Objetivo
Crear el modelo `PerfilOperativo` en la aplicación `usuarios` con relación `OneToOne` hacia `Usuario` para almacenar vehículo, placas, ruta, horario (`hora_inicio` y `hora_fin`) y disponibilidad de los usuarios con rol `operativo`.

## Cambios realizados
- **`usuarios/models.py`**:
  - Se agregó el modelo `PerfilOperativo` con relación `OneToOneField` (`related_name="perfil_operativo"`).
  - Campos incluidos: `vehiculo`, `placas`, `ruta`, `hora_inicio` (`TimeField`, opcional), `hora_fin` (`TimeField`, opcional), `disponibilidad` (`default=True`), `creado_en` y `actualizado_en`.
  - Restricción de unicidad insensible a mayúsculas sobre `placas` no vacías (`perfil_operativo_placas_unicas_ci`) y normalización a mayúsculas en `save()`.
  - Validación en `clean()` para restringir la asignación únicamente a usuarios con `rol == Rol.OPERATIVO`.
- **`usuarios/migrations/0010_perfiloperativo.py`**:
  - Se generó y aplicó la migración correspondiente al nuevo modelo.

## Relación con otras subtareas de HU-36 y HU-37
- Base de datos lista para **ST-231** (endpoints de administración y consulta), **ST-232** (pruebas de integración) y **ST-234** (validación de horario de turno en login).