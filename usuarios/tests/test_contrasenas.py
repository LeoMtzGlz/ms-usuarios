"""HU-15: pruebas del generador de contraseña temporal."""
import pytest
from django.contrib.auth.password_validation import validate_password

from usuarios.contrasenas import (
    LONGITUD_TEMPORAL,
    MAYUSCULAS,
    MINUSCULAS,
    NUMEROS,
    SIMBOLOS,
    generar_contrasena_temporal,
)


def test_tiene_doce_caracteres_por_defecto():
    assert len(generar_contrasena_temporal()) == LONGITUD_TEMPORAL == 12


@pytest.mark.parametrize("longitud", [8, 12, 20])
def test_respeta_la_longitud_pedida(longitud):
    assert len(generar_contrasena_temporal(longitud)) == longitud


def test_siempre_trae_mayuscula_minuscula_numero_y_simbolo():
    for _ in range(200):
        contrasena = generar_contrasena_temporal()
        assert any(c in MAYUSCULAS for c in contrasena)
        assert any(c in MINUSCULAS for c in contrasena)
        assert any(c in NUMEROS for c in contrasena)
        assert any(c in SIMBOLOS for c in contrasena)


def test_no_usa_caracteres_ambiguos():
    for _ in range(200):
        assert not set(generar_contrasena_temporal()) & set("O0Il1")


def test_cumple_la_politica_de_contrasenas():
    for _ in range(50):
        validate_password(generar_contrasena_temporal())


def test_dos_llamadas_dan_contrasenas_distintas():
    assert len({generar_contrasena_temporal() for _ in range(100)}) == 100


def test_rechaza_longitudes_menores_a_ocho():
    with pytest.raises(ValueError):
        generar_contrasena_temporal(7)
