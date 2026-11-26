# ST-68: Pruebas del registro

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Descripción:** Pruebas de los casos de error de `POST /api/v1/auth/registro/`.

## Resultado
Los 6 casos del backlog ya estaban probados a nivel serializer (`test_registro_serializer.py`, ST-65) y el caso correcto y el correo duplicado por HTTP (`test_registro_endpoint.py`, ST-66). Se agregó `usuarios/tests/test_registro_casos_http.py` con lo que faltaba por HTTP: teléfono duplicado, contraseñas distintas, contraseña débil, aviso de privacidad sin aceptar y campos obligatorios. Todas comprueban el `400 datos_invalidos`, el campo que falla y que no se crea cuenta, código ni notificación.

## Pruebas
docker compose run --rm api pytest usuarios/tests/test_registro_casos_http.py -v