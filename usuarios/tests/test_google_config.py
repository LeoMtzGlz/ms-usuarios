"""HU-33 / ST-218: GOOGLE_CLIENT_ID se lee del entorno (.env)."""
import importlib

import pytest

import config.settings


@pytest.fixture
def recargar_settings(monkeypatch):
    """Recarga config.settings con las variables de entorno de la prueba y la deja como estaba."""
    def recargar():
        return importlib.reload(config.settings)

    yield recargar
    monkeypatch.undo()
    importlib.reload(config.settings)


def test_lee_google_client_id_del_entorno(monkeypatch, recargar_settings):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456789012-abc.apps.googleusercontent.com")
    assert recargar_settings().GOOGLE_CLIENT_ID == "123456789012-abc.apps.googleusercontent.com"


def test_por_defecto_esta_vacio(monkeypatch, recargar_settings):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    assert recargar_settings().GOOGLE_CLIENT_ID == ""