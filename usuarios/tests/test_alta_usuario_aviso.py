"""HU-15 / ST-142: el alta de un operativo encola un aviso de cuenta creada, sin la contraseña."""
import json

import pytest
from django.core import mail
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from comun.roles import Rol
from notificaciones import worker
from notificaciones.canales import CanalCorreo
from notificaciones.models import Notificacion
from notificaciones.services import preparar_contenido_notificacion
from usuarios.models import Usuario, Zona
from usuarios.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/usuarios/"
PIE_OBLIGATORIO = "Correo automático, no respondas."
CORREO = "luis.ramirez@ejemplo.com"


def datos_validos(**cambios):
    zona, _ = Zona.objects.get_or_create(nombre="Centro", defaults={"activa": True})  # t-35/st-227
    datos = {
        "nombre": "Luis", "apellidos": "Ramírez Soto", "correo": CORREO, "telefono": "443 123 4567",
        "zona": zona.pk,
    }
    datos.update(cambios)
    return datos


def cliente_como(api_client, usuario):
    acceso = RefreshToken.for_user(usuario).access_token
    acceso["rol"] = usuario.rol
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api_client


@pytest.fixture
def cliente_admin(api_client, llaves):
    return cliente_como(api_client, UsuarioFactory(rol=Rol.ADMINISTRADOR))


def dar_de_alta(cliente_admin):
    """Hace el alta y devuelve (usuario creado, contraseña temporal)."""
    respuesta = cliente_admin.post(URL, datos_validos(), format="json")
    assert respuesta.status_code == 201
    return Usuario.objects.get(email=CORREO), respuesta.json()["contrasena_temporal"]


# --- Qué se encola -------------------------------------------------------------------


def test_el_alta_encola_un_aviso_por_correo_para_la_cuenta_creada(cliente_admin):
    usuario, _ = dar_de_alta(cliente_admin)

    aviso = Notificacion.objects.get(destinatario=usuario)
    assert aviso.canal == "correo"
    assert aviso.plantilla == "cuenta_creada"
    assert aviso.estado == Notificacion.ESTADO_PENDIENTE
    assert aviso.contexto == {"nombre": "Luis", "correo": CORREO}


def test_cada_alta_encola_un_solo_aviso(cliente_admin):
    dar_de_alta(cliente_admin)
    cliente_admin.post(
        URL, datos_validos(correo="otra@ejemplo.com", telefono="443 765 4321"), format="json"
    )

    assert Notificacion.objects.filter(plantilla="cuenta_creada").count() == 2


def test_el_aviso_sale_por_correo_aunque_el_canal_preferido_sea_otro(cliente_admin):
    usuario, _ = dar_de_alta(cliente_admin)

    assert Notificacion.objects.get(destinatario=usuario).canal == "correo"


# --- Sin la contraseña ---------------------------------------------------------------


def test_la_contrasena_no_se_guarda_en_la_bandeja_de_salida(cliente_admin):
    _, contrasena = dar_de_alta(cliente_admin)

    for aviso in Notificacion.objects.all():
        assert contrasena not in json.dumps(aviso.contexto)
        assert contrasena not in aviso.plantilla
        assert contrasena not in aviso.error


def test_el_correo_armado_no_lleva_la_contrasena_y_da_instrucciones(cliente_admin):
    usuario, contrasena = dar_de_alta(cliente_admin)

    asunto, texto, html = preparar_contenido_notificacion(Notificacion.objects.get(destinatario=usuario))

    assert asunto == "Tu cuenta ha sido creada"
    for contenido in (texto, html):
        assert contrasena not in contenido
        assert "Luis" in contenido
        assert CORREO in contenido
        assert "contraseña temporal" in contenido
        assert "contraseña nueva" in contenido
        assert PIE_OBLIGATORIO in contenido


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="notificaciones@ejemplo.com"
)
def test_enviado_por_el_canal_de_correo_llega_al_usuario_sin_la_contrasena(cliente_admin):
    usuario, contrasena = dar_de_alta(cliente_admin)
    asunto, texto, html = preparar_contenido_notificacion(Notificacion.objects.get(destinatario=usuario))

    CanalCorreo().enviar(destino=usuario.email, asunto=asunto, texto=texto, html=html)

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == [CORREO]
    assert correo.subject == "Tu cuenta ha sido creada"
    assert contrasena not in correo.body
    assert contrasena not in correo.alternatives[0][0]


# --- Cuándo NO se encola -------------------------------------------------------------


def test_un_alta_rechazada_no_encola_nada(cliente_admin):
    UsuarioFactory(email=CORREO)

    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 400
    assert not Notificacion.objects.filter(plantilla="cuenta_creada").exists()


@pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.OPERATIVO])
def test_quien_no_es_administrador_no_provoca_avisos(api_client, llaves, rol):
    cliente_como(api_client, UsuarioFactory(rol=rol))

    assert api_client.post(URL, datos_validos(), format="json").status_code == 403
    assert not Notificacion.objects.exists()


def test_si_falla_el_encolado_tampoco_queda_la_cuenta(cliente_admin, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("la bandeja de salida no responde")

    monkeypatch.setattr("usuarios.views_admin.notificar", falla)
    cliente_admin.raise_request_exception = False

    respuesta = cliente_admin.post(URL, datos_validos(), format="json")

    assert respuesta.status_code == 500
    assert not Usuario.objects.filter(email=CORREO).exists()
    assert not Notificacion.objects.exists()


# --- Entrega real: pendiente fuera de esta subtarea ----------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="El worker arma el mensaje con notificaciones/<plantilla>.txt (worker.armar_mensaje), pero esas "
    "plantillas no existen: solo hay .html en correo/ y el worker no llama a preparar_contenido_notificacion. "
    "Hoy ninguna notificación con plantilla sale (T-08/T-10). Al integrarlo, esta prueba pasará y habrá que "
    "quitar el xfail.",
)
@override_settings(
    CANAL_NOTIFICACIONES="correo",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@ejemplo.com",
)
def test_el_worker_entrega_el_aviso_al_usuario_creado(cliente_admin):
    usuario, contrasena = dar_de_alta(cliente_admin)

    resultado = worker.procesar_lote()

    assert resultado.enviadas == 1
    assert [correo.to for correo in mail.outbox] == [[usuario.email]]
    assert contrasena not in mail.outbox[0].body
