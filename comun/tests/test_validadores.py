import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from comun.validadores import MayusculaYNumeroValidator

validador = MayusculaYNumeroValidator()

def codigos(excinfo):
    return {e.code for e in excinfo.value.error_list}


@pytest.mark.parametrize("password", ["Segura123", "ÑandúRojo7", "x9Y"])
def test_acepta_con_mayuscula_y_numero(password):
    validador.validate(password)  # no lanza


def test_rechaza_sin_mayuscula():
    with pytest.raises(ValidationError) as e:
        validador.validate("segura123")
    assert codigos(e) == {"password_sin_mayuscula"}


def test_rechaza_sin_numero():
    with pytest.raises(ValidationError) as e:
        validador.validate("SeguraSinNumero")
    assert codigos(e) == {"password_sin_numero"}


def test_reporta_ambos_errores_a_la_vez():
    with pytest.raises(ValidationError) as e:
        validador.validate("segura")
    assert codigos(e) == {"password_sin_mayuscula", "password_sin_numero"}


def test_superindice_no_cuenta_como_numero():
    with pytest.raises(ValidationError) as e:
        validador.validate("Segura²")
    assert "password_sin_numero" in codigos(e)


def test_mensajes_en_espanol():
    with pytest.raises(ValidationError) as e:
        validador.validate("segura")
    texto = " ".join(e.value.messages)
    assert "mayúscula" in texto and "número" in texto

def test_esta_registrado_en_la_politica_del_proyecto():
    """Integración con settings (USR-102): validate_password lo aplica."""
    with pytest.raises(ValidationError) as e:
        validate_password("abcdefgh1")
    assert "password_sin_mayuscula" in codigos(e)