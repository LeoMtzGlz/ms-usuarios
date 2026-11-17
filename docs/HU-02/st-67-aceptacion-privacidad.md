# HU-02 — Registrarme como cliente

## ST-67 : [Backend] Guardar la aceptación del aviso de privacidad

**Estado:** En revisión.

**Responsable:** VAZQUEZ AVALOS ISIS LIZBETH (isis0015)

**Revisa:** AVILA GARCIA DANNA GERALDINE (DannaGe) · continúa con ST-68

### Descripción
Cuando una persona se registra y acepta el aviso de privacidad, se guarda **cuándo** lo aceptó (`acepto_privacidad_en = now()`) y **qué versión** aceptó (`version_privacidad`, tomada de `settings`).

### Resultado

| Archivo | Qué contiene |
| --- | --- |
| `usuarios/privacidad.py` (nuevo) | `version_vigente()`, `datos_aceptacion_privacidad()` y la revisión de la configuración al arrancar |
| `usuarios/serializers.py` | `RegistroSerializer.create()` usa `datos_aceptacion_privacidad()` |
| `usuarios/apps.py` | Registra la revisión de la configuración en `ready()` |
| `usuarios/tests/test_privacidad.py` (nuevo) | Pruebas de la subtarea |

`datos_aceptacion_privacidad()` devuelve:

```python
{
    "acepto_privacidad_en": timezone.now(),                        # fecha y hora con zona horaria
    "version_privacidad": settings.VERSION_AVISO_PRIVACIDAD,       # versión vigente
}
```

Es el único lugar donde se decide qué se guarda al aceptar el aviso. HU-28 (aceptar una versión nueva del aviso) debe reutilizarlo.

### Reglas
- La fecha y la versión **las pone el servidor**. Si el cliente manda `acepto_privacidad_en` o `version_privacidad` en la petición, se ignoran.
- Sin `acepto_privacidad = true`, el registro se rechaza y no se guarda nada (ST-65).
- Cada registro guarda la versión **vigente en ese momento**. Si el aviso cambia, los usuarios anteriores conservan la versión que aceptaron.
- La respuesta del registro no expone la fecha ni la versión.

### Configuración

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `VERSION_AVISO_PRIVACIDAD` | `1.0` | Versión vigente del aviso de privacidad |

Al arrancar (`manage.py check`, `runserver`, `migrate`), Django revisa que la variable sea válida:

| Error | Cuándo |
| --- | --- |
| `usuarios.E001` | `VERSION_AVISO_PRIVACIDAD` está vacía |
| `usuarios.E002` | Tiene más de 20 caracteres y no cabe en `version_privacidad` |

### Dónde se ve
En el admin de Django, dentro de cada usuario, en la sección **Privacidad**. La fecha es de solo lectura.

### Pruebas

```bash
docker compose exec api pytest usuarios/tests/test_privacidad.py -v
docker compose exec api python manage.py check
```