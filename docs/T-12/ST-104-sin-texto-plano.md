# T-12 — Configurar la política de contraseñas y el hash

## ST-104 : Prueba de que no hay texto plano

**Estado:** Terminada. En revisión (PR ```t-12/st-104 : Prueba de que no hay texto plano```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Prueba que las contraseñas nunca se guardan en texto plano y que se usa el hasher definido en T-12.
- El campo ```password``` empieza con ```argon2```.
- PBKDF2 queda como respaldo: un hash antiguo sigue funcionando y se actualiza a Argon2.

### Resultado: 
```usuarios/tests/test_hash_password.py```, sobre la configuración de ```PASSWORD_HASHERS``` en ```config/settings.py``` (st-102).

Las pruebas usan la configuración real del proyecto, sin reemplazar ```PASSWORD_HASHERS```: si alguien quita Argon2 o cambia su orden en ```config/settings.py```, fallan.

### Pruebas: 
```usuarios/tests/test_hash_password.py``` (4 passed)
- ```test_set_password_guarda_argon2``` → ```set_password``` guarda un hash Argon2 y ```check_password``` funciona.
- ```test_create_user_guarda_argon2``` → ```create_user``` guarda un hash Argon2.
- ```test_valor_real_en_postgresql``` → el valor leído directo de la base empieza con ```argon2$argon2id$``` y no contiene la contraseña.
- ```test_hash_pbkdf2_antiguo_funciona_y_se_actualiza``` → un hash PBKDF2 sigue sirviendo y se convierte a Argon2.