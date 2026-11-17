# T-12 — Configurar la política de contraseñas y el hash

## ST-105 : Documentar la política

**Estado:** Terminada. En revisión (PR ```t-12/st-105 : Documentar la política```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Documentar la política de contraseñas de T-12 en el README y en el ```help_text``` del serializer.

### Resultado: 
- ```README.md```, sección «Política de contraseñas (T-12): reglas y dónde está cada una, formato del error 400, almacenamiento con Argon2id y PBKDF2 de respaldo, y cómo cambiar la política.
- ```usuarios/serializers.py```: el campo ```password``` del ```RegistroSerializer``` usa ```help_text=AYUDA_POLITICA_PASSWORD``` (```comun/validadores.py```), visible en ```/api/docs/```.

Pendiente: los serializers de recuperación (st-108) y cambio de contraseña (st-112) deben usar la misma constante cuando se integren.

Pruebas: no hay cambios de lógica; la política la cubren ```comun/tests/test_validadores.py``` y ```comun/tests/test_hash_password.py```.