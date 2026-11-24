# ST-82: Crear endpoint de login

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Descripción:** Se expone la ruta POST /api/v1/auth/login/ usando el CustomTokenObtainPairSerializer creado en la ST-81.

## Resultado
- `usuarios/views.py`: clase `CustomTokenObtainPairView`.
- `usuarios/urls.py`: ruta `login/`.
- `config/urls.py`: se incluye `usuarios.urls` bajo `api/v1/auth/`.
- `usuarios/tests/test_login.py`: 4 pruebas (éxito, credenciales inválidas, pendiente e inactivo).

## Pruebas
docker compose run --rm api pytest usuarios/tests/test_login.py -v