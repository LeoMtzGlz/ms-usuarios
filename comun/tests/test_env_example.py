"""Pruebas de .env.example: que al copiarlo a .env, django-environ lea valores limpios.

django-environ no quita los comentarios al final de la línea: en `EMAIL_PORT=587 # x`
el valor es "587 # x". Estas pruebas evitan que vuelva a pasar.
"""
import re

import environ
import pytest
from django.conf import settings

ENV_EXAMPLE = settings.BASE_DIR / ".env.example"
DOCKER_COMPOSE = settings.BASE_DIR / "docker-compose.yml"


def _variables():
    """Pares (nombre, valor) de .env.example, tal como los ve django-environ, sin comentarios."""
    pares = []
    for linea in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        nombre, _, valor = linea.partition("=")
        pares.append((nombre.strip(), valor))
    return pares


@pytest.fixture
def env_example(monkeypatch):
    """environ.Env cargado con .env.example, sin tocar el os.environ real."""
    monkeypatch.setattr(environ.Env, "ENVIRON", {})
    environ.Env.read_env(ENV_EXAMPLE)
    return environ.Env()


def test_ningun_valor_tiene_comentarios():
    con_comentario = [nombre for nombre, valor in _variables() if "#" in valor]
    assert con_comentario == [], "Los comentarios van en su propia línea, arriba de la variable"


def test_ningun_valor_tiene_espacios_al_final():
    con_espacios = [nombre for nombre, valor in _variables() if valor != valor.rstrip()]
    assert con_espacios == []


def test_los_valores_numericos_y_booleanos_se_pueden_convertir(env_example):
    assert env_example.int("EMAIL_PORT") == 587
    assert env_example.bool("EMAIL_USE_TLS") is True
    assert env_example.bool("DEBUG") is True


def test_los_valores_vacios_quedan_vacios(env_example):
    for nombre in ("EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL", "CLAVE_CIFRADO_2FA"):
        assert env_example.str(nombre) == "", nombre


def test_database_url_coincide_con_docker_compose(env_example):
    compose = DOCKER_COMPOSE.read_text(encoding="utf-8")
    esperado = {
        clave: re.search(rf"^\s*{clave}:\s*(\S+)\s*$", compose, re.MULTILINE).group(1)
        for clave in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    }

    bd = env_example.db("DATABASE_URL")

    assert bd["USER"] == esperado["POSTGRES_USER"]
    assert bd["PASSWORD"] == esperado["POSTGRES_PASSWORD"]
    assert bd["NAME"] == esperado["POSTGRES_DB"]
