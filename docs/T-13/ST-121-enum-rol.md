# T-13 — Definir los roles y las clases de permiso

## ST-121 : Crear el enum Rol con TextChoices

**Estado:** Terminada. Integrada en development antes de la Guía de PR (commit ```de85e02c20c56```, PR ```t-13/st-121 : Crear el enum Rol con TextChoices```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Enum Rol con ADMINISTRADOR, CLIENTE y OPERATIVO para T-13. 
- Rol por defecto para Usuario: Cliente.
- Rol por defecto para Superusuario: ADMINISTRADOR

### Resultado: 
```comun/roles.py```, usado en el campo rol del modelo ```Usuario```; migración en ```usuarios/0002_rol_textchoices```. 

Valores: 
- ```ADMINISTRADOR = "administrador", "Administrador"```
- ```CLIENTE = "cliente", "Cliente"```
- ```OPERATIVO = "operativo", "Operativo"```

Restricción en PostgreSQL: 
- ```CheckConstraint``` ```usuario_rol_valido```: la columna ```rol``` solo acepta los valores del enum (```rol IN ('administrador', 'cliente', 'operativo')```). 
- La base de datos rechaza un rol inventado aunque se guarde sin pasar por las validaciones de Django, por ejemplo con ```.update()``` o SQL directo.

### ¿Por qué Rol vive en ```comun/```?
- ```comun/permisos.py``` (st-122) necesita el enum para comparar el claim ```rol``` del token. Si viviera en ```usuarios/models.py```, ```comun``` dependería de los modelos de ```usuarios``` y se arriesgaría a una importación circular.
- Es un contrato compartido: el claim ```rol``` del JWT lo leen los permisos, el comando ```crear_admin``` (st-124) y los demás microservicios. Tenerlo en el paquete común deja un solo lugar de referencia.
- Por eso sus valores no se cambian sin acuerdo de todo el equipo.

### Pruebas: 
```comun/tests/test_roles.py```
- ```test_miembros_del_enum``` → el enum tiene exactamente ADMINISTRADOR, CLIENTE y OPERATIVO.
- ```test_valores_no_cambian``` → los valores siguen siendo ```administrador```, ```cliente``` y ```operativo``` (protege el contrato del JWT).
- ```test_rol_por_defecto_es_cliente``` → un usuario nuevo queda con rol Cliente.
- ```test_superusuario_es_administrador``` → ```create_superuser``` asigna Administrador.
- ```test_full_clean_rechaza_rol_inventado``` → Django rechaza un rol fuera del enum al validar el modelo.