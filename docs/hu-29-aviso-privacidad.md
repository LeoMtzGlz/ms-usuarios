# HU-29 · Aceptar nuevas versiones del aviso de privacidad

## Objetivo
Permitir que el usuario consulte la versión vigente del aviso de privacidad, acepte cambios y que el login indique si requiere aceptar una nueva versión.

## Cambios técnicos realizados
- **Configuración:** Se agregaron las variables `VERSION_AVISO_PRIVACIDAD` y `URL_AVISO_PRIVACIDAD` en el archivo `.env` y `config/settings.py`.
- **Modelo:** Se actualizan los campos `acepto_privacidad_en` (fecha) y `version_privacidad` (texto) del modelo `Usuario`.
- **Vistas (Endpoints):**
  - `GET /api/v1/privacidad/`: Devuelve la versión vigente y la URL.
  - `POST /api/v1/privacidad/aceptar/`: Registra la fecha actual y la versión vigente.
- **Login:** El serializer de login ahora incluye el campo booleano `requiere_aceptar_privacidad`.

## Reglas de negocio
- Si `usuario.version_privacidad` es menor a `settings.VERSION_AVISO_PRIVACIDAD`, el login devolverá `requiere_aceptar_privacidad: true`.

## Endpoints afectados
- `GET /api/v1/privacidad/` (Público)
- `POST /api/v1/privacidad/aceptar/` (Requiere Token)
- `POST /api/v1/auth/login/` (Respuesta modificada) 