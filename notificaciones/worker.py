"""t-10/st-51: lógica del worker que vacía la bandeja de salida.

El comando ``procesar_notificaciones`` solo repite ``procesar_lote()`` cada 5 s.
Aquí vive todo lo demás para poder probarlo sin bucles ni sleeps.

Puntos de extensión (cada uno lo completa otra subtarea, sin tocar el resto):
- ``antes_de_enviar()``  -> t-11/st-57: límite diario por canal (cambio de canal o espera).
- ``manejar_fallo()``    -> t-10/st-52: reintentos (intentos += 1) y respaldo a correo.
"""
import logging
from dataclasses import dataclass

from django.db import transaction
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from notificaciones.models import CanalNotificacion, Notificacion

logger = logging.getLogger("svc.notificaciones")

TAMANO_LOTE = 20
INTERVALO_SEGUNDOS = 5
LARGO_MAXIMO_ERROR = 500

# Función de st-35 que devuelve el canal (Consola, Correo, WhatsApp) para un nombre de canal.
# Confirmar el nombre con l22420438 cuando st-35/st-36 entren a development.
RESOLVER_CANAL = "notificaciones.canales.obtener_canal"
ASUNTO_POR_DEFECTO = "Aviso de tu cuenta"


@dataclass
class Resultado:
    enviadas: int = 0
    fallidas: int = 0
    pospuestas: int = 0

    @property
    def total(self) -> int:
        return self.enviadas + self.fallidas + self.pospuestas


def cargar_resolver(ruta: str = RESOLVER_CANAL):
    """Importa la función que entrega el canal. Falla en voz alta si st-35 todavía no está."""
    return import_string(ruta)


def tomar_pendientes(tamano: int = TAMANO_LOTE) -> list[Notificacion]:
    """Bloquea hasta ``tamano`` pendientes, las más viejas primero.

    ``skip_locked`` hace que otro worker se salte las filas que este ya tomó, así dos
    workers nunca envían la misma. ``of=("self",)`` bloquea solo la notificación, no al
    usuario que trae ``select_related``. Debe llamarse dentro de ``transaction.atomic()``.
    """
    return list(
        Notificacion.objects.select_for_update(skip_locked=True, of=("self",))
        .select_related("destinatario")
        .filter(estado=Notificacion.ESTADO_PENDIENTE)
        .order_by("creado_en", "id")[:tamano]
    )


def destino_de(notificacion: Notificacion) -> str:
    usuario = notificacion.destinatario
    if notificacion.canal == CanalNotificacion.WHATSAPP:
        return usuario.telefono or ""
    return usuario.email


def armar_mensaje(notificacion: Notificacion) -> tuple[str, str]:
    """Devuelve (asunto, texto) con la plantilla ``notificaciones/<plantilla>.txt``.

    Confirmar con l22420438 (st-35) y l22420450 (st-41): si el canal renderiza la
    plantilla por su cuenta, esta función se reduce a pasarle los datos.
    """
    contexto = notificacion.contexto or {}
    texto = render_to_string(f"notificaciones/{notificacion.plantilla}.txt", contexto)
    asunto = contexto.get("asunto") or ASUNTO_POR_DEFECTO
    return asunto, texto.strip()


def antes_de_enviar(notificacion: Notificacion) -> bool:
    """Punto de st-57. True = enviar ahora; False = dejarla pendiente para otro ciclo.

    st-57 puede además cambiar ``notificacion.canal`` (WhatsApp al límite -> correo).
    """
    return True


def limpiar_error(notificacion: Notificacion, exc: Exception) -> str:
    """Texto del error para guardar, sin el código aunque el proveedor lo repita (T-07)."""
    texto = f"{exc.__class__.__name__}: {exc}"
    for clave, valor in (notificacion.contexto or {}).items():
        if "codigo" in clave.lower() and valor:
            texto = texto.replace(str(valor), "***")
    return texto[:LARGO_MAXIMO_ERROR]


def manejar_fallo(notificacion: Notificacion, exc: Exception) -> None:
    """Punto de st-52. Por ahora: marcar como fallida y guardar el error.

    st-52 cambia el cuerpo: intentos += 1, dejarla pendiente hasta 3 fallos y, si es
    WhatsApp, crear la copia por correo.
    """
    notificacion.estado = Notificacion.ESTADO_FALLIDA
    notificacion.error = limpiar_error(notificacion, exc)
    notificacion.save(update_fields=["estado", "error", "actualizado_en"])


def marcar_enviada(notificacion: Notificacion) -> None:
    """Marca como enviada y vacía el contexto, que lleva el código (regla de T-07)."""
    notificacion.estado = Notificacion.ESTADO_ENVIADA
    notificacion.error = ""
    notificacion.contexto = {}
    notificacion.save(update_fields=["estado", "error", "contexto", "actualizado_en"])


def procesar(notificacion: Notificacion, obtener_canal) -> str:
    """Envía una notificación ya bloqueada. Devuelve 'enviada', 'fallida' o 'pospuesta'."""
    if not antes_de_enviar(notificacion):
        return "pospuesta"
    try:
        # Savepoint: si algo falla aquí, el resto del lote sigue con la transacción sana.
        with transaction.atomic():
            asunto, texto = armar_mensaje(notificacion)
            canal = obtener_canal(notificacion.canal)
            canal.enviar(destino_de(notificacion), asunto, texto)
            marcar_enviada(notificacion)
    except Exception as exc:  # cualquier fallo de una notificación no debe tumbar al worker
        logger.warning(
            "No se pudo enviar la notificación %s por %s: %s",
            notificacion.pk, notificacion.canal, exc.__class__.__name__,
        )
        manejar_fallo(notificacion, exc)
        return "fallida"
    return "enviada"


def procesar_lote(tamano: int = TAMANO_LOTE, obtener_canal=None) -> Resultado:
    """Toma un lote de pendientes, las envía y guarda su estado en una sola transacción."""
    obtener_canal = obtener_canal or cargar_resolver()
    resultado = Resultado()
    with transaction.atomic():
        for notificacion in tomar_pendientes(tamano):
            estado = procesar(notificacion, obtener_canal)
            campo = f"{estado}s"  # enviadas, fallidas, pospuestas
            setattr(resultado, campo, getattr(resultado, campo) + 1)
    return resultado
