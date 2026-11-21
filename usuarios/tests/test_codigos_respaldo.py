import re

import pytest
from django.contrib.auth.hashers import check_password

from usuarios.dos_factores import generar_codigos_respaldo, usar_codigo_respaldo
from usuarios.models import CodigoRespaldo
from usuarios.tests.factories import UsuarioFactory

FORMATO = re.compile(r"^[A-HJKMNP-Z2-9]{3}-[A-HJKMNP-Z2-9]{3}$")

@pytest.fixture
def cliente(db):
    return UsuarioFactory()

@pytest.fixture
def otro(db):
    return UsuarioFactory()


@pytest.mark.django_db
class TestGenerar:
    def test_genera_10_unicos_con_formato(self, cliente):
        codigos = generar_codigos_respaldo(cliente)
        assert len(codigos) == 10 == len(set(codigos))
        assert all(FORMATO.match(c) for c in codigos)

    def test_se_guardan_con_hash(self, cliente):
        codigos = generar_codigos_respaldo(cliente)
        guardados = list(CodigoRespaldo.objects.filter(usuario=cliente))
        assert len(guardados) == 10
        for cr in guardados:
            assert all(c.replace("-", "") not in cr.codigo_hash for c in codigos)
        assert any(check_password(codigos[0].replace("-", ""), cr.codigo_hash) for cr in guardados)

    def test_regenerar_invalida_los_anteriores(self, cliente):
        viejos = generar_codigos_respaldo(cliente)
        generar_codigos_respaldo(cliente)
        assert CodigoRespaldo.objects.filter(usuario=cliente).count() == 10
        assert usar_codigo_respaldo(cliente, viejos[0]) is False


@pytest.mark.django_db
class TestUsar:
    def test_un_solo_uso(self, cliente):
        codigo = generar_codigos_respaldo(cliente)[0]
        assert usar_codigo_respaldo(cliente, codigo) is True
        assert usar_codigo_respaldo(cliente, codigo) is False

    def test_acepta_minusculas_y_sin_guion(self, cliente):
        codigo = generar_codigos_respaldo(cliente)[0]
        assert usar_codigo_respaldo(cliente, codigo.replace("-", "").lower()) is True

    def test_no_sirve_para_otro_usuario(self, cliente, otro):
        codigo = generar_codigos_respaldo(cliente)[0]
        generar_codigos_respaldo(otro)
        assert usar_codigo_respaldo(otro, codigo) is False