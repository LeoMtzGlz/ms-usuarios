"""HU-23 / ST-173: pruebas de anonimizar_usuario() según docs/HU-23/ST-172-datos-anonimizados.md."""
import json

import pytest
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.test import RequestFactory
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from comun.models import EventoAuditoria
from comun.roles import Rol
from notificaciones.models import Notificacion
from usuarios.anonimizacion import anonimizar_usuario, correo_anonimo, esta_anonimizado
from usuarios.models import Canal, CodigoVerificacion, Dispositivo2FA, Estado, RegistroAcceso, Usuario
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db


def anonimizar(usuario, **kwargs):
    anonimizar_usuario(usuario, **kwargs)
    usuario.refresh_from_db()
    return usuario


# --- Valores genéricos únicos ---------------------------------------------------------

def test_reemplaza_nombre_correo_y_telefono():
    usuario = anonimizar(UsuarioFactory(first_name="María", last_name="Hernández", telefono="+524431234567"))

    assert usuario.first_name == "Usuario"
    assert usuario.last_name == "eliminado"
    assert usuario.email == f"eliminado-{usuario.pk}@anonimo.invalid"
    assert usuario.telefono is None


def test_correos_anonimos_no_chocan_entre_si():
    """El correo es único en la base: dos cuentas eliminadas no pueden quedar con el mismo."""
    primero = anonimizar(UsuarioFactory())
    segundo = anonimizar(UsuarioFactory())

    assert primero.email != segundo.email
    assert Usuario.objects.filter(email__endswith="@anonimo.invalid").count() == 2


def test_libera_el_correo_y_el_telefono_para_una_cuenta_nueva():
    anonimizar(UsuarioFactory(email="maria@ejemplo.com", telefono="+524431234567"))

    nueva = UsuarioFactory(email="maria@ejemplo.com", telefono="+524431234567")
    assert nueva.pk


def test_no_queda_ningun_dato_personal():
    usuario = UsuarioFactory(email="maria.hernandez@ejemplo.com", first_name="María", last_name="Hernández",
                             telefono="+524431234567")
    anonimizar(usuario)

    valores = json.dumps(list(Usuario.objects.filter(pk=usuario.pk).values()), default=str)
    for dato in ("maria.hernandez", "María", "Hernández", "4431234567"):
        assert dato not in valores


# --- Contraseña inutilizable ------------------------------------------------------------

def test_contrasena_inutilizable():
    usuario = anonimizar(UsuarioFactory())

    assert usuario.has_usable_password() is False
    assert not usuario.check_password(PASSWORD_PRUEBA)


def test_no_puede_iniciar_sesion_ni_con_el_correo_original():
    usuario = UsuarioFactory(email="maria@ejemplo.com")
    anonimizar(usuario)

    request = RequestFactory().post("/api/v1/auth/login/")  # django-axes exige el request
    assert authenticate(request, email="maria@ejemplo.com", password=PASSWORD_PRUEBA) is None
    assert authenticate(request, email=correo_anonimo(usuario), password=PASSWORD_PRUEBA) is None


# --- Cuenta inactiva y sesiones cerradas -------------------------------------------------

def test_queda_inactiva_y_cierra_los_access_tokens():
    usuario = UsuarioFactory(token_version=4)
    anonimizar(usuario)

    assert usuario.estado == Estado.INACTIVO
    assert usuario.is_active is False
    assert usuario.token_version == 5


def test_refresh_tokens_a_la_lista_negra(llaves):
    usuario = UsuarioFactory()
    RefreshToken.for_user(usuario)
    RefreshToken.for_user(usuario)
    otro = UsuarioFactory()
    RefreshToken.for_user(otro)

    anonimizar(usuario)

    assert BlacklistedToken.objects.filter(token__user=usuario).count() == 2
    assert not BlacklistedToken.objects.filter(token__user=otro).exists()


def test_token_ya_en_lista_negra_no_se_duplica(llaves):
    usuario = UsuarioFactory()
    RefreshToken.for_user(usuario).blacklist()

    anonimizar(usuario)

    assert BlacklistedToken.objects.filter(token__user=usuario).count() == 1
    assert OutstandingToken.objects.filter(user=usuario).count() == 1


def test_pierde_acceso_al_admin_y_permisos():
    usuario = UsuarioFactory(is_staff=True, is_superuser=True)
    usuario.groups.add(Group.objects.create(name="soporte"))

    anonimizar(usuario)

    assert usuario.is_staff is False
    assert usuario.is_superuser is False
    assert not usuario.groups.exists()


def test_reinicia_verificaciones_y_canal():
    usuario = anonimizar(UsuarioFactory(email_verificado=True, telefono_verificado=True,
                                        canal_preferido=Canal.WHATSAPP, debe_cambiar_password=True))

    assert usuario.email_verificado is False
    assert usuario.telefono_verificado is False
    assert usuario.canal_preferido == Canal.CORREO
    assert usuario.debe_cambiar_password is False


# --- Lo que se conserva ---------------------------------------------------------------------

def test_conserva_id_rol_fechas_y_privacidad():
    aceptado = timezone.now()
    usuario = UsuarioFactory(rol=Rol.OPERATIVO, acepto_privacidad_en=aceptado, version_privacidad="2026-10")
    pk, alta = usuario.pk, usuario.date_joined

    anonimizar(usuario)

    assert usuario.pk == pk
    assert usuario.rol == Rol.OPERATIVO
    assert usuario.date_joined == alta
    assert usuario.acepto_privacidad_en == aceptado
    assert usuario.version_privacidad == "2026-10"


def test_conserva_historial_de_accesos_y_bitacora():
    usuario = UsuarioFactory()
    RegistroAcceso.objects.create(usuario=usuario, ip="201.141.10.5", dispositivo="Chrome", exitoso=True)
    EventoAuditoria.objects.create(usuario=usuario, accion="login")

    anonimizar(usuario)

    assert RegistroAcceso.objects.filter(usuario=usuario).count() == 1
    assert EventoAuditoria.objects.filter(usuario=usuario, accion="login").count() == 1


# --- Lo que se borra -------------------------------------------------------------------------

def test_borra_codigos_y_2fa():
    usuario = UsuarioFactory()
    CodigoVerificacion.objects.create(usuario=usuario, proposito="activacion", canal="correo",
                                      codigo_hash="x", expira_en=timezone.now())
    Dispositivo2FA.objects.create(usuario=usuario, secreto_cifrado="x")

    anonimizar(usuario)

    assert not CodigoVerificacion.objects.filter(usuario=usuario).exists()
    assert not Dispositivo2FA.objects.filter(usuario=usuario).exists()


def test_notificaciones_pendientes_se_borran_y_enviadas_quedan_sin_contexto():
    usuario = UsuarioFactory()
    pendiente = Notificacion.objects.create(destinatario=usuario, canal="correo", plantilla="bienvenida",
                                            contexto={"nombre": "María"})
    enviada = Notificacion.objects.create(destinatario=usuario, canal="correo", plantilla="codigo_activacion",
                                          contexto={"codigo": "123456"}, estado=Notificacion.ESTADO_ENVIADA)

    anonimizar(usuario)

    assert not Notificacion.objects.filter(pk=pendiente.pk).exists()
    enviada.refresh_from_db()
    assert enviada.contexto == {}


def test_respeta_las_notificaciones_que_pide_conservar():
    """ST-174 encola el correo de confirmación antes de anonimizar: no se toca."""
    usuario = UsuarioFactory()
    confirmacion = Notificacion.objects.create(destinatario=usuario, canal="correo", plantilla="cuenta_eliminada",
                                               contexto={"nombre": "María"})

    anonimizar(usuario, conservar_notificaciones=[confirmacion.pk])

    confirmacion.refresh_from_db()
    assert confirmacion.estado == Notificacion.ESTADO_PENDIENTE
    assert confirmacion.contexto == {"nombre": "María"}


def test_borra_el_correo_de_las_tablas_de_axes():
    usuario = UsuarioFactory(email="maria@ejemplo.com")
    comunes = {"ip_address": "201.141.10.5", "user_agent": "x", "http_accept": "x", "path_info": "/"}
    AccessAttempt.objects.create(username="MARIA@ejemplo.com", failures_since_start=1, **comunes)
    AccessFailureLog.objects.create(username="maria@ejemplo.com", **comunes)
    AccessLog.objects.create(username="maria@ejemplo.com", **comunes)
    AccessLog.objects.create(username="otra@ejemplo.com", **comunes)

    anonimizar(usuario)

    assert not AccessAttempt.objects.filter(username__iexact="maria@ejemplo.com").exists()
    assert not AccessFailureLog.objects.filter(username__iexact="maria@ejemplo.com").exists()
    assert not AccessLog.objects.filter(username__iexact="maria@ejemplo.com").exists()
    assert AccessLog.objects.filter(username="otra@ejemplo.com").exists()


# --- Otros usuarios, repetición y transacción --------------------------------------------------

def test_no_toca_a_otros_usuarios():
    usuario, otro = UsuarioFactory(), UsuarioFactory(first_name="Luis")
    CodigoVerificacion.objects.create(usuario=otro, proposito="activacion", canal="correo",
                                      codigo_hash="x", expira_en=timezone.now())

    anonimizar(usuario)
    otro.refresh_from_db()

    assert otro.first_name == "Luis"
    assert otro.estado == Estado.ACTIVO
    assert CodigoVerificacion.objects.filter(usuario=otro).exists()


def test_llamarla_dos_veces_no_cambia_nada_mas():
    usuario = anonimizar(UsuarioFactory())
    version = usuario.token_version

    anonimizar(usuario)

    assert esta_anonimizado(usuario)
    assert usuario.token_version == version


def test_si_algo_falla_no_se_anonimiza_nada(monkeypatch):
    usuario = UsuarioFactory(email="maria@ejemplo.com")

    def falla(*args, **kwargs):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(Usuario, "cambiar_estado", falla)
    with pytest.raises(RuntimeError):
        anonimizar_usuario(usuario)

    usuario.refresh_from_db()
    assert usuario.email == "maria@ejemplo.com"
    assert usuario.has_usable_password()


def test_registra_el_evento_sin_el_correo(caplog):
    usuario = UsuarioFactory(email="maria@ejemplo.com")

    with caplog.at_level("INFO", logger="svc.auditoria"):
        anonimizar_usuario(usuario)

    eventos = [json.loads(r.message) for r in caplog.records if r.name == "svc.auditoria"]
    assert any(e["accion"] == "cuenta_anonimizada" for e in eventos)
    assert "maria@ejemplo.com" not in caplog.text