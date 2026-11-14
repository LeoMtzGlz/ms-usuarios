# T-12 — Configurar la política de contraseñas y el hash

## ST-103 : Crear el validador de mayúscula y número

**Estado:** Terminada. Integrada en development antes de la Guía de PR (commit ```d08733e```, PR ```t-12/st-103 Validador mayuscula-numero- #14```).

**Responsable:** ORTIZ SIERRA LUDWIG IVÁN (Ludwig-Ivan)

### Descripción:
Validador propio para la política de contraseñas de T-12.
- La contraseña debe incluir al menos una letra mayúscula.
- La contraseña debe incluir al menos un número.
- Los mensajes de error están en español.

### Resultado: 
```comun/validadores.py```, clase ```MayusculaYNumeroValidator```, registrada en ```AUTH_PASSWORD_VALIDATORS``` de ```config/settings.py``` (st-102) junto con los validadores de Django: longitud mínima 8, contraseña común, solo números y similitud con el correo.

Errores que devuelve: 
- ```password_sin_mayuscula``` → "La contraseña debe incluir al menos una letra mayúscula."
- ```password_sin_numero``` → "La contraseña debe incluir al menos un número."

Lo aplica ```validate_password()``` en registro, recuperación y cambio de contraseña; st-80 (login, HU-05) depende de T-12.
  
Pruebas: ```comun/tests/test_validadores.py```