from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from usuarios.codigos import crear_codigo
from usuarios.models import Canal, CodigoVerificacion, Estado, Proposito
from usuarios.tests.factories import UsuarioFactory


URL = "/api/v1/auth/reenviar-codigo/"
URL_ACTIVAR = "/api/v1/auth/activar/"


@pytest.mark.django_db
def test_reenvio_genera_nuevo_codigo_e_invalida_el_anterior(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    codigo_viejo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal="correo",
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )

    CodigoVerificacion.objects.filter(pk=codigo_viejo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=61)
    )

    response = api_client.post(
        URL,
        {"identificador": usuario.email},
    )

    assert response.status_code == 200
    assert "mensaje" in response.data

    codigo_viejo.refresh_from_db()
    assert codigo_viejo.usado is True

    assert (
        CodigoVerificacion.objects.filter(
            usuario=usuario,
            proposito=Proposito.ACTIVACION,
            usado=False,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_reenvio_respuesta_generica_usuario_inexistente(api_client):
    response = api_client.post(
        URL,
        {"identificador": "noexiste@ejemplo.com"},
    )

    assert response.status_code == 200
    assert "mensaje" in response.data


@pytest.mark.django_db
def test_reenvio_no_hace_nada_si_usuario_esta_activo(api_client):
    usuario = UsuarioFactory(estado=Estado.ACTIVO)

    response = api_client.post(
        URL,
        {"identificador": usuario.email},
    )

    assert response.status_code == 200

    assert not CodigoVerificacion.objects.filter(usuario=usuario).exists()


@pytest.mark.django_db
def test_reenvio_bloqueado_durante_los_primeros_60_segundos(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    codigo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal="correo",
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )

    cantidad_anterior = CodigoVerificacion.objects.filter(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
    ).count()

    response = api_client.post(
        URL,
        {"identificador": usuario.email},
    )

    cantidad_actual = CodigoVerificacion.objects.filter(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
    ).count()

    assert response.status_code == 429
    assert "Retry-After" in response
    assert int(response["Retry-After"]) > 0

    assert cantidad_actual == cantidad_anterior

    codigo.refresh_from_db()
    assert codigo.usado is False


@pytest.mark.django_db
def test_reenvio_permitido_despues_de_60_segundos(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    codigo_viejo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal="correo",
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )

    CodigoVerificacion.objects.filter(pk=codigo_viejo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=60),
    )

    response = api_client.post(
        URL,
        {"identificador": usuario.email},
    )

    assert response.status_code == 200

    codigo_viejo.refresh_from_db()
    assert codigo_viejo.usado is True

    assert (
        CodigoVerificacion.objects.filter(
            usuario=usuario,
            proposito=Proposito.ACTIVACION,
            usado=False,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_reenvio_bloqueado_por_codigo_generado_durante_registro(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    codigo_inicial = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal="correo",
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )

    CodigoVerificacion.objects.filter(pk=codigo_inicial.pk).update(
        creado_en=timezone.now() - timedelta(seconds=20),
    )

    response = api_client.post(
        URL,
        {"identificador": usuario.email},
    )

    assert response.status_code == 429
    assert "Retry-After" in response
    assert int(response["Retry-After"]) > 0

    codigo_inicial.refresh_from_db()
    assert codigo_inicial.usado is False

    assert (
        CodigoVerificacion.objects.filter(
            usuario=usuario,
            proposito=Proposito.ACTIVACION,
        ).count()
        == 1
    )


# ==========================================
# Pruebas ST-77
# ==========================================


@pytest.mark.django_db
def test_st77_codigo_viejo_invalido_al_activar_cuenta(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)

    registro_viejo, codigo_viejo_claro = crear_codigo(
        usuario, Proposito.ACTIVACION, "correo"
    )
    CodigoVerificacion.objects.filter(pk=registro_viejo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=65)
    )

    codigos_enviados = []

    def capturar_notificacion(usr, plantilla, contexto, canal):
        codigos_enviados.append(contexto["codigo"])

    with patch(
        "usuarios.codigos.notificar", side_effect=capturar_notificacion
    ):
        resp_reenvio = api_client.post(
            URL,
            {"identificador": usuario.email},
        )

    assert resp_reenvio.status_code == 200
    assert len(codigos_enviados) == 1
    codigo_nuevo_claro = codigos_enviados[0]

    # Intentar activar con el código viejo -> debe rechazarlo.
    resp_activar_viejo = api_client.post(
        URL_ACTIVAR,
        {"identificador": usuario.email, "codigo": codigo_viejo_claro},
    )
    assert resp_activar_viejo.status_code == 400
    usuario.refresh_from_db()
    assert usuario.estado == Estado.PENDIENTE

    # Activar con el código nuevo -> debe funcionar.
    resp_activar_nuevo = api_client.post(
        URL_ACTIVAR,
        {"identificador": usuario.email, "codigo": codigo_nuevo_claro},
    )
    assert resp_activar_nuevo.status_code == 200
    usuario.refresh_from_db()
    assert usuario.estado == Estado.ACTIVO


@pytest.mark.django_db
def test_st77_cuenta_inexistente_e_inactiva_responden_igual(api_client):
    usuario_pendiente = UsuarioFactory(estado=Estado.PENDIENTE)
    usuario_inactivo = UsuarioFactory(estado=Estado.INACTIVO)

    resp_pendiente = api_client.post(
        URL,
        {"identificador": usuario_pendiente.email},
    )
    resp_inexistente = api_client.post(
        URL,
        {"identificador": "noexiste_st77@ejemplo.com"},
    )
    resp_inactivo = api_client.post(
        URL,
        {"identificador": usuario_inactivo.email},
    )

    assert resp_inexistente.status_code == resp_pendiente.status_code == 200
    assert resp_inexistente.data == resp_pendiente.data
    assert resp_inactivo.status_code == resp_pendiente.status_code == 200
    assert resp_inactivo.data == resp_pendiente.data

    assert not CodigoVerificacion.objects.filter(
        usuario=usuario_inactivo
    ).exists()


@pytest.mark.django_db
def test_st77_cuarto_reenvio_en_una_hora_rechazado(api_client):
    usuario = UsuarioFactory(estado=Estado.PENDIENTE)
    base_time = timezone.now()

    with patch("usuarios.codigos.timezone.now", return_value=base_time):
        registro_inicial, _ = crear_codigo(
            usuario, Proposito.ACTIVACION, "correo"
        )
        CodigoVerificacion.objects.filter(pk=registro_inicial.pk).update(
            creado_en=base_time
        )

    for intento in range(1, 4):
        momento = base_time + timedelta(seconds=61 * intento)
        with (
            patch("usuarios.reenvio.timezone.now", return_value=momento),
            patch("usuarios.codigos.timezone.now", return_value=momento),
        ):
            resp = api_client.post(
                URL,
                {"identificador": usuario.email},
            )
            assert resp.status_code == 200
            ultimo = (
                CodigoVerificacion.objects.filter(usuario=usuario)
                .order_by("-id")
                .first()
            )
            CodigoVerificacion.objects.filter(pk=ultimo.pk).update(
                creado_en=momento
            )

    # 4to reenvío dentro de la misma hora -> debe rechazarse con 429.
    momento_cuarto = base_time + timedelta(seconds=61 * 4)
    with patch("usuarios.reenvio.timezone.now", return_value=momento_cuarto):
        resp_cuarto = api_client.post(
            URL,
            {"identificador": usuario.email},
        )

    assert resp_cuarto.status_code == 429
    assert "Retry-After" in resp_cuarto
    assert int(resp_cuarto["Retry-After"]) > 0

    assert (
        CodigoVerificacion.objects.filter(
            usuario=usuario,
            proposito=Proposito.ACTIVACION,
        ).count()
        == 4
    )


# ST-62: Verificar que el reenvío respete el canal solicitado.
@pytest.mark.django_db
def test_reenvio_respeta_el_canal_solicitado(api_client):
    usuario = UsuarioFactory(
        estado=Estado.PENDIENTE,
        telefono="+524431000001",
    )

    codigo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal="correo",
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )
    CodigoVerificacion.objects.filter(pk=codigo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=61)
    )

    respuesta = api_client.post(
        URL,
        {"identificador": usuario.email, "canal": "whatsapp"},
        format="json",
    )

    assert respuesta.status_code == 200
    nuevo_codigo = CodigoVerificacion.objects.filter(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
    ).latest("creado_en")
    assert nuevo_codigo.canal == "whatsapp"


# ST-62: Verificar que el reenvío use el canal preferido cuando no se indica uno.
@pytest.mark.django_db
def test_reenvio_sin_canal_usa_el_preferido(api_client):
    usuario = UsuarioFactory(
        estado=Estado.PENDIENTE,
        telefono="+524431000001",
        canal_preferido=Canal.WHATSAPP,
    )

    codigo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal=Canal.CORREO,
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )
    CodigoVerificacion.objects.filter(pk=codigo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=61)
    )

    respuesta = api_client.post(
        URL,
        {"identificador": usuario.email},
        format="json",
    )

    assert respuesta.status_code == 200
    nuevo_codigo = CodigoVerificacion.objects.filter(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
    ).latest("creado_en")
    assert nuevo_codigo.canal == Canal.WHATSAPP


# ST-62: Verificar que el reenvío use correo si WhatsApp no está disponible.
@pytest.mark.django_db
def test_reenvio_respalda_a_correo_si_no_hay_telefono(api_client):
    usuario = UsuarioFactory(
        estado=Estado.PENDIENTE,
        telefono=None,
        canal_preferido=Canal.WHATSAPP,
    )

    codigo = CodigoVerificacion.objects.create(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
        canal=Canal.CORREO,
        codigo_hash="hash_falso",
        expira_en=timezone.now() + timedelta(minutes=10),
        usado=False,
    )
    CodigoVerificacion.objects.filter(pk=codigo.pk).update(
        creado_en=timezone.now() - timedelta(seconds=61)
    )

    respuesta = api_client.post(
        URL,
        {"identificador": usuario.email},
        format="json",
    )

    assert respuesta.status_code == 200
    nuevo_codigo = CodigoVerificacion.objects.filter(
        usuario=usuario,
        proposito=Proposito.ACTIVACION,
    ).latest("creado_en")
    assert nuevo_codigo.canal == Canal.CORREO
