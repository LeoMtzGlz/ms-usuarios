"""HU-21 / ST-164: cambio verificado del correo o teléfono propio."""

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from notificaciones.models import Notificacion
from notificaciones.worker import destino_de
from usuarios.models import CodigoVerificacion, Proposito
from usuarios.tests.factories import PASSWORD_PRUEBA, UsuarioFactory
from usuarios.tests.helpers_admin import api_de


SOLICITAR = "/api/v1/auth/perfil/contacto/solicitar/"
CONFIRMAR = "/api/v1/auth/perfil/contacto/confirmar/"


def solicitar(usuario, tipo, valor, password=PASSWORD_PRUEBA):
    return api_de(usuario).post(
        SOLICITAR,
        {"tipo": tipo, "valor": valor, "password": password},
        format="json",
    )


def codigo_enviado(usuario):
    return Notificacion.objects.filter(destinatario=usuario).latest("id").contexto["codigo"]


def confirmar(usuario, tipo, valor, codigo):
    return api_de(usuario).post(
        CONFIRMAR,
        {"tipo": tipo, "valor": valor, "codigo": codigo},
        format="json",
    )


@pytest.fixture
def usuario(db, llaves):
    return UsuarioFactory(
        email="actual@ejemplo.com",
        telefono="+524431234567",
        email_verificado=True,
        telefono_verificado=True,
    )


@pytest.mark.django_db
class TestSolicitudCambioContacto:
    def test_solicita_correo_y_no_cambia_el_actual(self, usuario):
        respuesta = solicitar(usuario, "correo", "Nuevo@Ejemplo.com")

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.email == "actual@ejemplo.com"

        registro = CodigoVerificacion.objects.get(
            usuario=usuario,
            proposito=Proposito.CAMBIO_CONTACTO,
        )
        notificacion = Notificacion.objects.get(destinatario=usuario)
        codigo = notificacion.contexto["codigo"]
        assert registro.canal == "correo"
        assert registro.codigo_hash != codigo
        assert check_password(
            f"{codigo}\x1fcorreo:nuevo@ejemplo.com",
            registro.codigo_hash,
        )
        assert notificacion.plantilla == "codigo_cambio_contacto"
        assert notificacion.contexto["destino_verificacion"] == "nuevo@ejemplo.com"
        assert destino_de(notificacion) == "nuevo@ejemplo.com"

    def test_solicita_telefono_normalizado_y_lo_envia_al_numero_nuevo(self, usuario):
        respuesta = solicitar(usuario, "telefono", "443 111 2233")

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.telefono == "+524431234567"
        notificacion = Notificacion.objects.get(destinatario=usuario)
        assert notificacion.canal == "whatsapp"
        assert notificacion.contexto["destino_verificacion"] == "+524431112233"
        assert destino_de(notificacion) == "+524431112233"

    def test_rechaza_password_incorrecta_sin_crear_codigo(self, usuario):
        respuesta = solicitar(usuario, "correo", "nuevo@ejemplo.com", "Incorrecta123")

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["password"] == ["La contraseña es incorrecta."]
        assert not CodigoVerificacion.objects.exists()
        assert not Notificacion.objects.exists()

    @pytest.mark.parametrize(
        ("tipo", "valor"),
        [
            ("correo", "actual@ejemplo.com"),
            ("telefono", "+524431234567"),
        ],
    )
    def test_rechaza_el_contacto_actual(self, usuario, tipo, valor):
        respuesta = solicitar(usuario, tipo, valor)

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["valor"] == ["Tu cuenta ya usa este dato."]

    @pytest.mark.parametrize("tipo", ["correo", "telefono"])
    def test_rechaza_un_contacto_que_pertenece_a_otra_cuenta(self, usuario, tipo):
        otra = UsuarioFactory()
        valor = otra.email.upper() if tipo == "correo" else otra.telefono

        respuesta = solicitar(usuario, tipo, valor)

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["valor"] == [
            "Este dato ya está registrado en otra cuenta."
        ]

    @pytest.mark.parametrize(
        ("tipo", "valor"),
        [("correo", "no-es-correo"), ("telefono", "123")],
    )
    def test_rechaza_contacto_con_formato_invalido(self, usuario, tipo, valor):
        respuesta = solicitar(usuario, tipo, valor)

        assert respuesta.status_code == 400
        assert "valor" in respuesta.data["campos"]

    def test_una_solicitud_nueva_anula_la_anterior(self, usuario):
        solicitar(usuario, "correo", "primero@ejemplo.com")
        primero = CodigoVerificacion.objects.get()

        solicitar(usuario, "correo", "segundo@ejemplo.com")

        primero.refresh_from_db()
        assert primero.usado is True
        assert CodigoVerificacion.objects.filter(usuario=usuario, usado=False).count() == 1


@pytest.mark.django_db
class TestConfirmacionCambioContacto:
    def test_confirma_correo_y_lo_marca_verificado(self, usuario):
        solicitar(usuario, "correo", "Nuevo@Ejemplo.com")

        respuesta = confirmar(usuario, "correo", "nuevo@ejemplo.com", codigo_enviado(usuario))

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.email == "nuevo@ejemplo.com"
        assert usuario.email_verificado is True
        assert CodigoVerificacion.objects.get(usuario=usuario).usado is True

    def test_confirma_telefono_normalizado_y_lo_marca_verificado(self, usuario):
        usuario.telefono_verificado = False
        usuario.save(update_fields=["telefono_verificado"])
        solicitar(usuario, "telefono", "443 111 2233")

        respuesta = confirmar(usuario, "telefono", "+52 443 111 2233", codigo_enviado(usuario))

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.telefono == "+524431112233"
        assert usuario.telefono_verificado is True

    def test_codigo_no_sirve_para_otro_contacto(self, usuario):
        solicitar(usuario, "correo", "destino@ejemplo.com")

        respuesta = confirmar(
            usuario,
            "correo",
            "otro@ejemplo.com",
            codigo_enviado(usuario),
        )

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["codigo"] == ["El código es incorrecto."]
        usuario.refresh_from_db()
        assert usuario.email == "actual@ejemplo.com"

    def test_codigo_incorrecto_no_cambia_el_contacto(self, usuario):
        solicitar(usuario, "correo", "nuevo@ejemplo.com")

        respuesta = confirmar(usuario, "correo", "nuevo@ejemplo.com", "000000")

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["codigo"] == ["El código es incorrecto."]
        usuario.refresh_from_db()
        assert usuario.email == "actual@ejemplo.com"

    def test_codigo_expirado_no_cambia_el_contacto(self, usuario):
        solicitar(usuario, "correo", "nuevo@ejemplo.com")
        CodigoVerificacion.objects.update(expira_en=timezone.now() - timedelta(seconds=1))

        respuesta = confirmar(usuario, "correo", "nuevo@ejemplo.com", codigo_enviado(usuario))

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["codigo"] == [
            "El código ya venció. Solicita uno nuevo."
        ]
        usuario.refresh_from_db()
        assert usuario.email == "actual@ejemplo.com"

    def test_bloquea_el_quinto_intento_incorrecto(self, usuario):
        solicitar(usuario, "correo", "nuevo@ejemplo.com")

        for _ in range(4):
            assert confirmar(usuario, "correo", "nuevo@ejemplo.com", "000000").status_code == 400
        quinta = confirmar(usuario, "correo", "nuevo@ejemplo.com", "000000")

        assert quinta.status_code == 400
        assert quinta.data["campos"]["codigo"] == [
            "Demasiados intentos. Solicita un código nuevo."
        ]
        assert CodigoVerificacion.objects.get(usuario=usuario).usado is True

    def test_codigo_es_de_un_solo_uso(self, usuario):
        solicitar(usuario, "correo", "primero@ejemplo.com")
        codigo = codigo_enviado(usuario)
        assert confirmar(usuario, "correo", "primero@ejemplo.com", codigo).status_code == 200

        respuesta = confirmar(usuario, "correo", "segundo@ejemplo.com", codigo)

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["codigo"] == ["El código es incorrecto."]

    def test_revalida_que_el_contacto_siga_disponible(self, usuario):
        solicitar(usuario, "correo", "nuevo@ejemplo.com")
        codigo = codigo_enviado(usuario)
        UsuarioFactory(email="nuevo@ejemplo.com")

        respuesta = confirmar(usuario, "correo", "nuevo@ejemplo.com", codigo)

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["valor"] == [
            "Este dato ya está registrado en otra cuenta."
        ]
        assert CodigoVerificacion.objects.get(usuario=usuario).usado is False


@pytest.mark.django_db
class TestSeguridadCambioContacto:
    @pytest.mark.parametrize("url", [SOLICITAR, CONFIRMAR])
    def test_sin_token_responde_401(self, api_client, url):
        respuesta = api_client.post(url, {}, format="json")

        assert respuesta.status_code == 401
        assert respuesta.data["codigo"] == "no_autenticado"

    @pytest.mark.parametrize("url", [SOLICITAR, CONFIRMAR])
    def test_password_temporal_responde_403(self, usuario, url):
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=["debe_cambiar_password"])

        respuesta = api_de(usuario).post(url, {}, format="json")

        assert respuesta.status_code == 403
        assert respuesta.data["codigo"] == "debe_cambiar_password"

    def test_otro_usuario_no_puede_confirmar_el_codigo(self, usuario):
        solicitar(usuario, "correo", "nuevo@ejemplo.com")
        codigo = codigo_enviado(usuario)
        atacante = UsuarioFactory()

        respuesta = confirmar(atacante, "correo", "nuevo@ejemplo.com", codigo)

        assert respuesta.status_code == 400
        assert respuesta.data["campos"]["codigo"] == ["El código es incorrecto."]
        usuario.refresh_from_db()
        assert usuario.email == "actual@ejemplo.com"
