# ST-230 — Modelo `PerfilOperativo` (HU-36)

## Objetivo
Crear el modelo `PerfilOperativo` en la aplicación `usuarios` con relación `OneToOne` hacia `Usuario` para almacenar vehículo, placas, ruta, horario y disponibilidad de los usuarios con rol `operativo`.

## Cambios realizados
- **`usuarios/models.py`**:
  - Se agregó el modelo `PerfilOperativo` con relación `OneToOneField` (`related_name="perfil_operativo"`).
  - Campos incluidos: `vehiculo`, `placas`, `ruta`, `horario`, `disponibilidad` (`default=True`), `creado_en` y `actualizado_en`.
  - Restricción de unicidad insensible a mayúsculas sobre `placas` no vacías (`perfil_operativo_placas_unicas_ci`) y normalización a mayúsculas en `save()`.
  - Validación en `clean()` para restringir la asignación únicamente a usuarios con `rol == Rol.OPERATIVO`.
- **`usuarios/migrations/`**:
  - Se generó y aplicó la migración correspondiente al nuevo modelo.

## Relación con otras subtareas de HU-36
- Base de datos lista para **ST-231** (endpoints de administración y consulta) y **ST-232** (pruebas de integración).

