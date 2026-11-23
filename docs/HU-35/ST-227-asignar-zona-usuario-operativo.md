# HU-35 — Asignar una zona a un usuario operativo

## ST-227. Agregar la zona al usuario operativo y al token

**Estado:** En desarrollo

**Responsable:** Alondra Alejandra López Medellin (22420450)

### 1. Descripción

El objetivo de esta subtarea es permitir que los usuarios con rol operativo tengan una zona asignada dentro del sistema.

La implementación contempla establecer una relación entre el modelo `Usuario` y el modelo `Zona`, permitir la asignación de una zona durante el alta administrativa del usuario y agregar el identificador de la zona a los tokens JWT.

Con esto se busca que el sistema pueda identificar la zona correspondiente a cada usuario operativo y que esta información esté disponible para los servicios que consumen el token.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/models.py` | Incorporar una relación entre `Usuario` y `Zona` mediante una llave foránea. |
| `usuarios/serializers_admin.py` | Permitir recibir, validar y guardar la zona asignada durante el alta de usuarios operativos. |
| `usuarios/tokens.py` | Agregar el claim `zona_id` al token JWT. |
| `usuarios/views_admin.py` | Actualizar la documentación de la respuesta del alta administrativa para incluir la zona. |
| `usuarios/migrations/` | Generar la migración correspondiente al nuevo campo de relación. |

### 3. Implementación realizada

**Relación Usuario-Zona**

Se contempla agregar una llave foránea al modelo `Usuario` para relacionarlo con el modelo `Zona`.

La relación utiliza `on_delete=models.PROTECT` para evitar eliminar zonas que estén asociadas a usuarios.

**Asignación de zona**

Se contempla actualizar `AltaUsuarioSerializer` para recibir el identificador de una zona activa y guardar la relación al crear un usuario operativo.

La validación debe impedir que se asignen zonas inactivas.

**Incorporación de la zona al JWT**

Se contempla modificar `CustomTokenObtainPairSerializer` para incluir el identificador de la zona mediante el claim:

`zona_id`

De esta manera, los tokens generados para los usuarios pueden contener el identificador de su zona asignada.

### 4. Migración de base de datos

La migración se generará utilizando Django mediante:

```bash
python manage.py makemigrations usuarios
```

Posteriormente se aplicará mediante:

```bash
python manage.py migrate
```

La migración debe conservar el modelo `Zona` existente y agregar únicamente la relación correspondiente al usuario.

### 5. Comprobaciones realizadas

**Comprobaciones pendientes de registrar:**

- Verificar que el usuario operativo pueda tener una zona asignada.
- Verificar que no se permita asignar una zona inactiva.
- Verificar que el token JWT incluya el claim `zona_id`.
- Comprobar que las migraciones estén actualizadas.
- Ejecutar las pruebas automatizadas del proyecto.

**Comandos de validación:**

```bash
ruff check .
python manage.py makemigrations --check --dry-run
pytest
```

**Resultados obtenidos:** Pendientes de ejecución y validación.

### 6. Resultado final

La finalidad de esta subtarea es incorporar la asignación de zonas a los usuarios operativos y permitir que el identificador de dicha zona esté disponible dentro del token JWT.

El resultado se considerará completado una vez que los cambios estén implementados, las comprobaciones sean satisfactorias y el Pull Request haya sido integrado en `development`.

### 7. Dependencias y coordinación

Esta subtarea pertenece a la HU-35: Asignar una zona a un usuario operativo.

**Dependencia previa:** ST-226, desarrollada por Katia Paola Victoria Escalera.

**Responsable de revisión y continuación:** Daniel Orlando Ceja Olloqui.

La siguiente subtarea es ST-228, correspondiente a las pruebas de la asignación de zona.

**Responsable de la actividad:** Alondra Alejandra López Medellin (22420450).