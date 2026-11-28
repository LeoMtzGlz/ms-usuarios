"""t-10/st-51: lógica del worker que vacía la bandeja de salida.

El comando ``procesar_notificaciones`` solo repite ``procesar_lote()`` cada 5 s.
Aquí vive todo lo demás para poder probarlo sin bucles ni sleeps.

t-10/st-52: ``manejar_fallo()`` reintenta hasta 3 fallos, respalda WhatsApp por correo al
tercero y ``procesar()`` descarta los códigos vencidos antes de enviar.

t-11/st-57: ``antes_de_enviar()`` aplica el límite diario por canal (cambio de canal o espera).
"""
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.module_loading import import_string

from notificaciones.models import CanalNotificacion, Notificacion
from notificaciones.services import contar_envios_hoy  # t-11/st-56

logger = logging.getLogger("svc.notificaciones")

TAMANO_LOTE = 20
INTERVALO_SEGUNDOS = 5
LARGO_MAXIMO_ERROR = 500
MAX_INTENTOS = 3  # fallos en total; sin espera, se reintenta en el siguiente ciclo de 5 s

# Función de T-07 (st-35/st-36) que devuelve el canal de envío. Recibe el canal de cada
# notificación (obtener_canal(notificacion.canal)), así cada una sale por el suyo.
RESOLVER_CANAL = "notificaciones.services.obtener_canal"
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


def tomar_pendientes(tamano: int = TAMANO_LOTE, excluir_canales=()) -> list[Notificacion]:
    """Bloquea hasta ``tamano`` pendientes, las más viejas primero.

    ``skip_locked`` hace que otro worker se salte las filas que este ya tomó, así dos
    workers nunca envían la misma. ``of=("self",)`` bloquea solo la notificación, no al
    usuario que trae ``select_related``. Debe llamarse dentro de ``transaction.atomic()``.

    t-11/st-57: ``excluir_canales`` deja fuera los canales que ya no pueden enviar hoy.
    """
    pendientes = (
        Notificacion.objects.select_for_update(skip_locked=True, of=("self",))
        .select_related("destinatario")
        .filter(estado=Notificacion.ESTADO_PENDIENTE)
    )
    if excluir_canales:
        pendientes = pendientes.exclude(canal__in=excluir_canales)
    return list(pendientes.order_by("creado_en", "id")[:tamano])


def destino_de(notificacion: Notificacion) -> str:
    usuario = notificacion.destinatario
    if notificacion.canal == CanalNotificacion.WHATSAPP:
        return usuario.telefono or ""
    return usuario.email


def armar_mensaje(notificacion: Notificacion) -> tuple[str, str]:
    """Devuelve (asunto, texto) con la plantilla ``notificaciones/<plantilla>.txt``.

    La interfaz Canal de st-35 recibe el texto ya armado, así que lo arma el worker.
    Las plantillas .txt las crea t-08/st-42; mientras no existan, la notificación queda
    fallida con TemplateDoesNotExist y el resto del lote sigue.
    """
    contexto = notificacion.contexto or {}
    texto = render_to_string(f"notificaciones/{notificacion.plantilla}.txt", contexto)
    asunto = contexto.get("asunto") or ASUNTO_POR_DEFECTO
    return asunto, texto.strip()


# t-11/st-57: setting con el tope diario de cada canal. Consola no tiene tope.
LIMITES_DIARIOS = {
    CanalNotificacion.CORREO: "LIMITE_DIARIO_CORREO",
    CanalNotificacion.WHATSAPP: "LIMITE_DIARIO_WHATSAPP",
}
# Días y canales de los que ya se avisó en el log, para no repetir la advertencia cada 5 s.
_avisos_de_limite: set[tuple[date, str]] = set()


def limite_alcanzado(canal: str) -> bool:
    """t-11/st-57: True si el canal ya llegó hoy a su tope diario."""
    setting = LIMITES_DIARIOS.get(canal)
    if setting is None:
        return False
    return contar_envios_hoy(canal) >= getattr(settings, setting)


def avisar_limite(canal: str) -> None:
    """t-11/st-57: una advertencia por canal y por día."""
    clave = (timezone.localdate(), canal)
    if clave in _avisos_de_limite:
        return
    _avisos_de_limite.add(clave)
    logger.warning("Límite diario de %s alcanzado: sus notificaciones esperan al día siguiente", canal)


def antes_de_enviar(notificacion: Notificacion) -> bool:
    """t-11/st-57: True = enviar ahora; False = dejarla pendiente para otro ciclo.

    - WhatsApp al límite: cambia la notificación a correo y la envía por ahí.
    - Correo al límite (o WhatsApp al límite sin correo disponible): queda pendiente hasta
      el día siguiente, cuando el conteo de ``contar_envios_hoy()`` vuelve a empezar.
    """
    if notificacion.canal == CanalNotificacion.WHATSAPP and limite_alcanzado(CanalNotificacion.WHATSAPP):
        if limite_alcanzado(CanalNotificacion.CORREO):
            avisar_limite(CanalNotificacion.CORREO)
            return False
        logger.info("Límite diario de WhatsApp alcanzado: la notificación %s sale por correo", notificacion.pk)
        notificacion.canal = CanalNotificacion.CORREO
        notificacion.save(update_fields=["canal", "actualizado_en"])
        return True
    if notificacion.canal == CanalNotificacion.CORREO and limite_alcanzado(CanalNotificacion.CORREO):
        avisar_limite(CanalNotificacion.CORREO)
        return False
    return True


def canales_en_espera() -> list[str]:
    """t-11/st-57: canales cuyas pendientes no pueden salir hoy.

    Correo al límite espera. WhatsApp solo espera si además está al límite, porque ya no
    puede pasarse a correo.
    """
    if not limite_alcanzado(CanalNotificacion.CORREO):
        return []
    en_espera = [CanalNotificacion.CORREO]
    if limite_alcanzado(CanalNotificacion.WHATSAPP):
        en_espera.append(CanalNotificacion.WHATSAPP)
    return en_espera


def limpiar_error(notificacion: Notificacion, exc: Exception) -> str:
    """Texto del error para guardar, sin el código aunque el proveedor lo repita (T-07)."""
    texto = f"{exc.__class__.__name__}: {exc}"
    for clave, valor in (notificacion.contexto or {}).items():
        if "codigo" in clave.lower() and valor:
            texto = texto.replace(str(valor), "***")
    return texto[:LARGO_MAXIMO_ERROR]


def codigo_vencido(notificacion: Notificacion, ahora: datetime | None = None) -> bool:
    """True si lleva ``codigo`` y ``minutos`` y ya pasó creado_en + minutos.

    Un ``minutos`` ausente, None o no numérico se trata como sin vencimiento (nunca truena).
    """
    contexto = notificacion.contexto or {}
    if not contexto.get("codigo"):
        return False
    ahora = ahora or timezone.now()
    try:  # nan/inf parsean como float pero timedelta los rechaza: también sin vencimiento
        return ahora > notificacion.creado_en + timedelta(minutes=float(contexto["minutos"]))
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def crear_respaldo_por_correo(notificacion: Notificacion) -> Notificacion:
    """Copia pendiente por correo (misma plantilla y contexto) con el creado_en original."""
    copia = Notificacion.objects.create(
        destinatario=notificacion.destinatario,
        canal=CanalNotificacion.CORREO,
        plantilla=notificacion.plantilla,
        contexto=notificacion.contexto,
    )
    # auto_now_add ignora creado_en al crear; el update lo fija para conservar el orden y el vencimiento.
    Notificacion.objects.filter(pk=copia.pk).update(creado_en=notificacion.creado_en)
    copia.creado_en = notificacion.creado_en
    return copia


def marcar_fallida(notificacion: Notificacion, error: str) -> None:
    """Fallo definitivo: guarda el error y vacía el contexto, que lleva el código."""
    notificacion.estado = Notificacion.ESTADO_FALLIDA
    notificacion.error = error
    notificacion.contexto = {}
    notificacion.save(update_fields=["estado", "error", "contexto", "intentos", "actualizado_en"])


def manejar_fallo(notificacion: Notificacion, exc: Exception) -> None:
    """Suma un intento; pendiente hasta MAX_INTENTOS fallos, luego fallida (y respaldo si WhatsApp)."""
    error = limpiar_error(notificacion, exc)  # antes de vaciar el contexto
    notificacion.intentos += 1
    if notificacion.intentos < MAX_INTENTOS:
        notificacion.error = error
        notificacion.save(update_fields=["intentos", "error", "actualizado_en"])
        return
    contexto = notificacion.contexto
    try:
        with transaction.atomic():  # savepoint: copia y marca fallida son todo o nada
            if notificacion.canal == CanalNotificacion.WHATSAPP and not codigo_vencido(notificacion):
                crear_respaldo_por_correo(notificacion)
            marcar_fallida(notificacion, error)
    except Exception as exc_respaldo:
        # Sin perder el mensaje: queda pendiente (con el contexto) y se reintenta el cierre en el
        # siguiente ciclo; el resto del lote sigue.
        logger.error(
            "No se pudo cerrar la notificación %s tras %s fallos: %s",
            notificacion.pk, notificacion.intentos, exc_respaldo.__class__.__name__,
        )
        notificacion.estado = Notificacion.ESTADO_PENDIENTE
        notificacion.contexto = contexto
        notificacion.error = error
        notificacion.save(update_fields=["estado", "error", "contexto", "intentos", "actualizado_en"])


def marcar_enviada(notificacion: Notificacion) -> None:
    """Marca como enviada y vacía el contexto, que lleva el código (regla de T-07)."""
    notificacion.estado = Notificacion.ESTADO_ENVIADA
    notificacion.error = ""
    notificacion.contexto = {}
    notificacion.save(update_fields=["estado", "error", "contexto", "actualizado_en"])


def procesar(notificacion: Notificacion, obtener_canal) -> str:
    """Envía una notificación ya bloqueada. Devuelve 'enviada', 'fallida' o 'pospuesta'."""
    if codigo_vencido(notificacion):
        marcar_fallida(notificacion, "Código vencido: no se envió")
        return "fallida"
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
        en_espera = canales_en_espera()  # t-11/st-57
        for canal in en_espera:
            avisar_limite(canal)
        for notificacion in tomar_pendientes(tamano, excluir_canales=en_espera):
            estado = procesar(notificacion, obtener_canal)
            campo = f"{estado}s"  # enviadas, fallidas, pospuestas
            setattr(resultado, campo, getattr(resultado, campo) + 1)
    return resultado
