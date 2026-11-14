# T-13 — Definir los roles y las clases de permiso

## ST-124. Crear el comando crear_admin <correo>

**Estado:** Completada  
**Responsable:** López Rivas Estefanía (l21420212)

### 1. Descripción

Se creó el comando `crear_admin`, que da de alta una cuenta con rol Administrador y pide la contraseña por consola. Es la forma recomendada de crear un administrador: la API no lo permite (T-13, criterios 1 y 4). También existe `createsuperuser` de Django.

### 2. Cambios realizados

| Archivo | Cambio |
|---|---|
| `usuarios/management/__init__.py` | Nuevo (vacío): registra la carpeta de comandos |
| `usuarios/management/commands/__init__.py` | Nuevo (vacío) |
| `usuarios/management/commands/crear_admin.py` | El comando |
| `usuarios/tests/test_crear_admin.py` | 10 pruebas |

No se modificó ningún archivo existente ni se creó ninguna migración.

### 3. Uso

```bash
docker compose run --rm api python manage.py crear_admin admin@ejemplo.com
docker compose run --rm api python manage.py crear_admin admin@ejemplo.com \
    --nombre Ana --apellidos "López" --telefono "443 123 4567"
```

El comando pide la contraseña dos veces. Tiene tres intentos; si no coinciden o no cumplen la política de T-12 (mínimo 8 caracteres, una mayúscula y un número), no crea la cuenta.

### 4. Cómo funciona

- Usa `create_superuser()` del manager, que ya pone rol administrador, estado activo, correo verificado, `is_staff` e `is_superuser`.
- Valida la contraseña con `validate_password()`, así que aplica los mismos validadores que `AUTH_PASSWORD_VALIDATORS`, incluida la similitud con el correo y el nombre.
- Valida el formato del correo con `validate_email()` y rechaza uno ya registrado sin importar mayúsculas.
- Rechaza un teléfono repetido o inválido.
- Normaliza el teléfono a E.164 con `normalizar_telefono()`.
- Registra el evento `admin_creado` con `registrar_evento()`, sin la contraseña.
- Crea la cuenta y registra el evento dentro de una transacción.

### 5. Pruebas

```bash
docker compose run --rm api pytest usuarios/tests/test_crear_admin.py -v
```

| Prueba | Qué verifica |
|---|---|
| `test_crea_administrador_activo` | Rol administrador, estado activo, staff, superusuario y correo verificado |
| `test_guarda_la_contrasena_con_argon2` | La contraseña se guarda como hash Argon2 |
| `test_registra_el_evento_sin_la_contrasena` | Evento `admin_creado` sin datos sensibles |
| `test_normaliza_el_telefono` | `443 123 4567` se guarda como `+524431234567` |
| `test_rechaza_correo_invalido` | Un correo sin formato válido, como `hola`, no crea la cuenta |
| `test_rechaza_correo_existente_sin_importar_mayusculas` | No crea un segundo usuario con el mismo correo |
| `test_rechaza_telefono_existente` | No crea un segundo usuario con el mismo teléfono |
| `test_rechaza_telefono_invalido` | Teléfono con formato inválido |
| `test_vuelve_a_pedir_si_no_coinciden` | Vuelve a pedir la contraseña si la confirmación no coincide |
| `test_rechaza_contrasena_debil_tres_veces` | Tras tres contraseñas débiles no crea la cuenta ni registra el evento |

### 6. Resultado

El comando quedó disponible como `python manage.py crear_admin <correo>`, con 10 pruebas en verde.

**ST-124 finalizada.**

**Responsable de la actividad:** López Rivas Estefanía (l21420212).