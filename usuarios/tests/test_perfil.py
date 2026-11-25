"""HU-21 / ST-163: GET y PATCH /api/v1/auth/perfil/."""

import pytest

from comun.roles import Rol
from usuarios.models import Canal
from usuarios.tests.helpers_admin import api_de
from usuarios.tests.factories import UsuarioFactory


URL = "/api/v1/auth/perfil/"
CAMPOS_RESPUESTA = {
    "id",
    "nombre",
    "apellidos",
    "correo",
    "telefono",
    "canal_preferido",
    "rol",
    "estado",
}


@pytest.fixture
def usuario(db, llaves):
    return UsuarioFactory(
        first_name="Ana",
        last_name="López",
        canal_preferido=Canal.CORREO,
    )


@pytest.mark.django_db
class TestConsultaPerfil:
    def test_devuelve_solo_el_perfil_de_la_sesion(self, usuario):
        otro = UsuarioFactory(first_name="Persona ajena")

        respuesta = api_de(usuario).get(URL)

        assert respuesta.status_code == 200
        assert set(respuesta.data) == CAMPOS_RESPUESTA
        assert respuesta.data["id"] == str(usuario.pk)
        assert respuesta.data["nombre"] == "Ana"
        assert respuesta.data["apellidos"] == "López"
        assert respuesta.data["correo"] == usuario.email
        assert respuesta.data["id"] != str(otro.pk)

    @pytest.mark.parametrize("rol", Rol.values)
    def test_los_tres_roles_consultan_su_propio_perfil(self, llaves, rol):
        usuario = UsuarioFactory(rol=rol)

        respuesta = api_de(usuario).get(URL)

        assert respuesta.status_code == 200
        assert respuesta.data["id"] == str(usuario.pk)

    def test_no_expone_datos_sensibles(self, usuario):
        respuesta = api_de(usuario).get(URL)

        for campo in (
            "password",
            "token_version",
            "debe_cambiar_password",
            "is_staff",
            "is_superuser",
        ):
            assert campo not in respuesta.data


@pytest.mark.django_db
class TestEdicionPerfil:
    def test_edita_nombre_apellidos_y_canal_preferido(self, usuario):
        respuesta = api_de(usuario).patch(
            URL,
            {
                "nombre": "María Fernanda",
                "apellidos": "Pérez Soto",
                "canal_preferido": Canal.WHATSAPP,
            },
            format="json",
        )

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.first_name == "María Fernanda"
        assert usuario.last_name == "Pérez Soto"
        assert usuario.canal_preferido == Canal.WHATSAPP

    def test_edicion_parcial_conserva_los_demas_datos(self, usuario):
        apellidos = usuario.last_name

        respuesta = api_de(usuario).patch(URL, {"nombre": "Nuevo nombre"}, format="json")

        assert respuesta.status_code == 200
        usuario.refresh_from_db()
        assert usuario.first_name == "Nuevo nombre"
        assert usuario.last_name == apellidos

    @pytest.mark.parametrize(
        "campo,valor",
        [
            ("email", "otro@ejemplo.com"),
            ("correo", "otro@ejemplo.com"),
            ("telefono", "+524431112233"),
            ("rol", Rol.ADMINISTRADOR),
            ("estado", "inactivo"),
            ("password", "NuevaSegura1"),
            ("token_version", 99),
        ],
    )
    def test_rechaza_campos_no_editables(self, usuario, campo, valor):
        valores_antes = (usuario.email, usuario.telefono, usuario.rol, usuario.estado)

        respuesta = api_de(usuario).patch(URL, {campo: valor}, format="json")

        assert respuesta.status_code == 400
        assert respuesta.data["codigo"] == "datos_invalidos"
        assert campo in respuesta.data["campos"]
        assert respuesta.data["campos"][campo] == [
            "Este campo no se puede modificar desde el perfil."
        ]
        usuario.refresh_from_db()
        assert (usuario.email, usuario.telefono, usuario.rol, usuario.estado) == valores_antes

    def test_rechaza_canal_invalido(self, usuario):
        respuesta = api_de(usuario).patch(URL, {"canal_preferido": "sms"}, format="json")

        assert respuesta.status_code == 400
        assert "canal_preferido" in respuesta.data["campos"]

    def test_rechaza_whatsapp_si_la_cuenta_no_tiene_telefono(self, llaves):
        usuario = UsuarioFactory(
            telefono=None,
            canal_preferido=Canal.CORREO,
        )

        respuesta = api_de(usuario).patch(
            URL,
            {"canal_preferido": Canal.WHATSAPP},
            format="json",
        )

        assert respuesta.status_code == 400
        assert respuesta.data["codigo"] == "datos_invalidos"
        assert respuesta.data["campos"]["canal_preferido"] == [
            "Registra un teléfono antes de elegir WhatsApp."
        ]
        usuario.refresh_from_db()
        assert usuario.canal_preferido == Canal.CORREO

    def test_put_y_delete_no_estan_permitidos(self, usuario):
        cliente = api_de(usuario)

        assert cliente.put(URL, {"nombre": "X"}, format="json").status_code == 405
        assert cliente.delete(URL).status_code == 405


@pytest.mark.django_db
class TestSeguridadPerfil:
    @pytest.mark.parametrize("metodo", ["get", "patch"])
    def test_sin_token_responde_401(self, api_client, metodo):
        respuesta = getattr(api_client, metodo)(URL, {}, format="json")

        assert respuesta.status_code == 401
        assert respuesta.data["codigo"] == "no_autenticado"

    @pytest.mark.parametrize("metodo", ["get", "patch"])
    def test_contrasena_temporal_responde_403(self, usuario, metodo):
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=["debe_cambiar_password"])

        respuesta = getattr(api_de(usuario), metodo)(URL, {}, format="json")

        assert respuesta.status_code == 403
        assert respuesta.data["codigo"] == "debe_cambiar_password"
