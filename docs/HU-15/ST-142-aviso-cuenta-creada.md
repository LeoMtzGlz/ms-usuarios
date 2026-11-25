# ST-142 - Encolar el aviso de cuenta creada

## Objetivo

Cuando un administrador da de alta a un usuario operativo (ST-140), la persona debe enterarse de que tiene cuenta y
saber cómo entrar. HU-15 pide "un aviso de cuenta creada **sin la contraseña**": la contraseña temporal solo viaja
en la respuesta del alta, nunca por correo (ST-141).

Esta subtarea encola ese aviso y crea su plantilla. El envío real lo hace el worker de `notificaciones` (ver
"Limitación conocida").

## Qué pasa al dar de alta a alguien

`POST /api/v1/usuarios/` (`UsuariosView.post`, `usuarios/views_admin.py`):

```text
with transaction.atomic():
    usuario = serializer.save(contrasena=contrasena)   # ST-140
    notificar(usuario, plantilla="cuenta_creada",
              contexto={"nombre": ..., "correo": ...}, canal=CORREO)   # ST-142
```

| Dato de la notificación | Valor |
| --- | --- |
| `destinatario` | La cuenta recién creada |
| `canal` | `correo`, siempre (HU-15 lo pide por correo, sin importar `canal_preferido`) |
| `plantilla` | `cuenta_creada` |
| `contexto` | `{"nombre": primer nombre, "correo": correo de la cuenta}` |
| `estado` | `pendiente`; el worker la envía después |

- **Misma transacción que el alta.** Si falla el encolado, tampoco queda la cuenta, y el administrador recibe `500`
  en vez de una cuenta de la que nadie fue avisado. Hay una prueba que lo verifica.
- **Un alta rechazada no encola nada** (duplicados, datos inválidos, sin permiso).
- **La contraseña nunca entra al contexto.** La bandeja de salida es una tabla de la base: cualquier cosa que se
  ponga en `contexto` queda guardada hasta que el worker la envíe.

## La plantilla `cuenta_creada`

`notificaciones/templates/notificaciones/correo/cuenta_creada.html`, registrada en `PLANTILLAS_CORREO`
(`notificaciones/plantillas.py`) con el asunto **"Tu cuenta ha sido creada"**. Hereda de `base.html`, así que lleva
el encabezado y el pie común ("Correo automático, no respondas.").

| Variable | Obligatoria | Uso |
| --- | --- | --- |
| `nombre` | No (por defecto "usuario") | Saludo |
| `correo` | No | Se muestra como usuario para iniciar sesión |
| `url_login` | No | Si viene, agrega el botón "Iniciar sesión". Hoy nadie la envía: el proyecto no tiene una URL de login configurada |
| `asunto` | No | Reemplaza el asunto por defecto, igual que en las otras plantillas |

Lo que dice el correo, en orden:

1. Un administrador creó una cuenta para ti.
2. Pide a quien te dio de alta tu **contraseña temporal**; por seguridad no se envía por correo.
3. Inicia sesión con tu correo (o con tu teléfono) y esa contraseña.
4. El sistema te pedirá elegir una contraseña nueva antes de continuar (`debe_cambiar_password=True`).
5. Si no esperabas esta cuenta, avisa al administrador.

## Cambio en pruebas ajenas (T-08 / ST-42)

ST-42 entregó **5** plantillas y `test_total_plantillas_es_cinco` fijaba ese número. Con `cuenta_creada` son 6, así
que en `notificaciones/tests/test_plantillas_correo.py`:

- `test_total_plantillas_es_cinco` pasa a `test_total_plantillas_es_seis` (espera 6).
- `test_renderizar_5_plantillas_con_pie_comun` pasa a `test_renderizar_plantillas_con_pie_comun` y suma la fila de
  `cuenta_creada`.

No cambia ninguna aserción sobre las otras cinco plantillas.

## Pruebas

`usuarios/tests/test_alta_usuario_aviso.py`:

| Prueba | Qué garantiza |
| --- | --- |
| `test_el_alta_encola_un_aviso_por_correo_para_la_cuenta_creada` | Destinatario, canal, plantilla, estado y contexto exactos |
| `test_cada_alta_encola_un_solo_aviso` | Una notificación por alta, no más |
| `test_el_aviso_sale_por_correo_aunque_el_canal_preferido_sea_otro` | El canal es `correo` |
| `test_la_contrasena_no_se_guarda_en_la_bandeja_de_salida` | La contraseña no está en ningún campo de `Notificacion` |
| `test_el_correo_armado_no_lleva_la_contrasena_y_da_instrucciones` | Texto y HTML: sin contraseña, con nombre, correo, instrucciones y pie común |
| `test_enviado_por_el_canal_de_correo_llega_al_usuario_sin_la_contrasena` | Con `CanalCorreo` y el backend de pruebas, el correo llega al usuario creado sin la contraseña |
| `test_un_alta_rechazada_no_encola_nada` | Duplicados: cero avisos |
| `test_quien_no_es_administrador_no_provoca_avisos` | 403 para cliente y operativo: cero avisos |
| `test_si_falla_el_encolado_tampoco_queda_la_cuenta` | Atomicidad: `500`, sin cuenta y sin aviso |
| `test_el_worker_entrega_el_aviso_al_usuario_creado` | **`xfail` estricto**: ver abajo |

## Limitación conocida: el worker todavía no entrega ninguna plantilla

El criterio de HU-15 "se envía por correo un aviso" **no se cumple de punta a punta hoy**, y no por esta subtarea:

- `notificaciones/worker.py` arma el mensaje con `armar_mensaje()`, que renderiza `notificaciones/<plantilla>.txt`.
- Esas plantillas `.txt` no existen. T-08 creó solo plantillas `.html` en `correo/`, y el worker no llama a
  `preparar_contenido_notificacion()`, que sí sabe usarlas.
- Resultado verificado: una notificación `bienvenida` o `cuenta_creada` termina en `fallida` con
  `TemplateDoesNotExist: notificaciones/<plantilla>.txt`. Le pasa lo mismo a los códigos de activación del registro.
- La rama `feature/t-10-reintentos-respaldo` (reintentos y respaldo) tampoco lo cambia.

`test_el_worker_entrega_el_aviso_al_usuario_creado` documenta el problema con un `xfail` estricto: cuando el worker
use las plantillas HTML, pasará y habrá que quitarle la marca. Mientras tanto, las pruebas de esta subtarea cubren
lo que sí es suyo: que el aviso se encole bien, que su contenido sea correcto y que se pueda enviar por el canal de
correo.

## Pendiente en otras subtareas

- **ST-143:** pruebas generales de HU-15.
- **T-08 / T-10:** que el worker envíe las plantillas HTML (`armar_mensaje` o `preparar_contenido_notificacion`).
- **URL de login:** si el equipo quiere el botón "Iniciar sesión", hace falta un setting con la URL del frontend y
  pasarla como `url_login` al encolar.
