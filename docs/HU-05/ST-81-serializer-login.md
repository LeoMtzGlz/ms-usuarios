# ST-81: Extender TokenObtainPairSerializer con los claims

**Estado:** En revisión
**Responsable:** Danna Geraldine Ávila García (DannaGe)
**Descripción:** Se extendió el serializer de SimpleJWT para agregar los claims requeridos por el backlog (`rol`, `email_verificado`, `token_version`, `debe_cambiar_password`).

## Resultado
Se creó `usuarios/serializers.py` con la clase `CustomTokenObtainPairSerializer`. Esta clase revisa el estado del usuario antes de emitir el token (lanzando las excepciones `CuentaPendiente` y `CuentaInactiva`), actualiza el `last_login` y agrega los datos del usuario en la respuesta final.