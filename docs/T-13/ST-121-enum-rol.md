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
  
Pruebas: ```comun/test/test_roles.py```