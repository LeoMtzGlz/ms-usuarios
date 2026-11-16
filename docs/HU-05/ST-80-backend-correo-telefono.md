# ST-80: Backend de autenticación por correo o teléfono

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Descripción:** Backend de Django que permite autenticar a un usuario usando su correo electrónico (ignorando mayúsculas) o su número de teléfono (normalizado a E.164).

## Resultado
Se creó `usuarios/backends.py` con la clase `EmailOrPhoneBackend`. Se agregó a `AUTHENTICATION_BACKENDS` en `config/settings.py` uniéndolo con el backend de django-axes. Se implementó un hash de relleno cuando el usuario no existe para evitar ataques de enumeración de usuarios. Se agregaron pruebas unitarias.