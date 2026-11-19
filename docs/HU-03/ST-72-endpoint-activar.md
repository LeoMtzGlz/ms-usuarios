# ST-72 · Endpoint de activación

## Qué hace
POST /api/v1/auth/activar/ recibe identificador (correo o teléfono) y código de 6 dígitos, valida vigencia, intentos y uso, y activa la cuenta.

## Archivos
- usuarios/codigos.py: verificar_codigo() - busca el código pendiente más reciente, verifica expiración, bloquea al 5to intento fallido, compara con check_password y lo marca como usado.
- usuarios/serializers.py: ActivarSerializer - busca usuario por correo (iexact) o teléfono (E.164), llama a verificar_codigo() y traduce errores a codigo_expirado / codigo_bloqueado / codigo_invalido.
- usuarios/views.py: ActivarCuentaView - activa la cuenta (Estado.ACTIVO) y marca email_verificado o telefono_verificado según el canal del código.
- usuarios/urls.py: ruta activar/.
- config/urls.py: namespace explícito auth para que reverse("auth:registro") funcione.

## Respuestas
- 200: {id, correo, estado: "activo", mensaje: "Cuenta activada."}
- 400: identificador no existe, codigo incorrecto / vencido / bloqueado.

## Cómo probar
docker compose exec api pytest -q
203 passed.
