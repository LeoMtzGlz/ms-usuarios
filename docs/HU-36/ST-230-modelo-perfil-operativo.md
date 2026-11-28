# ST-230 — Modelo `PerfilOperativo` (HU-36)

## Objetivo
Crear el modelo `PerfilOperativo` en la aplicación `usuarios` con relación `OneToOne` hacia `Usuario` para almacenar vehículo, placas, ruta, horario (`hora_inicio` y `hora_fin`) y disponibilidad de los usuarios con rol `operativo`.

## Cambios realizados
- **`usuarios/models.py`**:
  - Se agregó el modelo `PerfilOperativo` con relación `OneToOneField` (`related_name="perfil_operativo"`).
  - Campos incluidos: `vehiculo`, `placas`, `ruta`, `hora_inicio` (`TimeField`, opcional), `hora_fin` (`TimeField`, opcional), `disponibilidad` (`default=True`), `creado_en` y `actualizado_en`.
  - Restricción de unicidad insensible a mayúsculas sobre `placas` no vacías (`perfil_operativo_placas_unicas_ci`) y normalización a mayúsculas en `save()`.
  - Restricción `CheckConstraint` (`perfil_operativo_horario_completo`) para garantizar que `hora_inicio` y `hora_fin` se capturen juntos o ambos sean nulos.
  - Validación de `Rol.OPERATIVO` en `clean()`, invocada desde `save()` mediante `self.full_clean()`.
- **`usuarios/migrations/0010_perfiloperativo.py`**:
  - Migración generada y aplicada con las restricciones del modelo.
- **`usuarios/tests/test_perfil_operativo_modelo.py`**:
  - Pruebas unitarias de unicidad de placas sin distinguir mayúsculas (`abc123` vs `ABC123`), rechazo de usuarios sin rol `operativo`, consistencia de `hora_inicio`/`hora_fin` y manejo de placas vacías.
  