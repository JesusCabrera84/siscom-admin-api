"""Tests para app.core.config: parseo de ALLOWED_ORIGINS desde variables de entorno.

Regresión de un fallo en producción: con el campo declarado como `list[str]` sin
`NoDecode`, pydantic-settings corría `json.loads` sobre el valor crudo antes de
llegar al validador, y cualquier CSV reventaba el arranque de la app.
"""

import pytest

from app.core.config import Settings

# _env_file=None aísla el test del .env local del desarrollador.
DEFAULT_ORIGINS = Settings(_env_file=None).ALLOWED_ORIGINS


def build_settings(monkeypatch, raw: str) -> Settings:
    monkeypatch.setenv("ALLOWED_ORIGINS", raw)
    return Settings(_env_file=None)


def test_parses_comma_separated_origins(monkeypatch):
    settings = build_settings(
        monkeypatch, "https://a.example.com,https://b.example.com"
    )
    assert settings.ALLOWED_ORIGINS == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_parses_json_array_origins(monkeypatch):
    settings = build_settings(
        monkeypatch, '["https://a.example.com", "https://b.example.com"]'
    )
    assert settings.ALLOWED_ORIGINS == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_csv_with_ports_and_schemes_survives(monkeypatch):
    """El valor real de producción: los ':' y '//' no deben confundir al parser."""
    settings = build_settings(
        monkeypatch,
        "http://10.8.0.1:5160,http://10.8.0.1:8100,https://geminislabs.com",
    )
    assert settings.ALLOWED_ORIGINS == [
        "http://10.8.0.1:5160",
        "http://10.8.0.1:8100",
        "https://geminislabs.com",
    ]


def test_strips_whitespace_around_origins(monkeypatch):
    settings = build_settings(
        monkeypatch, " https://a.example.com , https://b.example.com "
    )
    assert settings.ALLOWED_ORIGINS == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_strips_trailing_slash(monkeypatch):
    settings = build_settings(monkeypatch, "https://a.example.com/")
    assert settings.ALLOWED_ORIGINS == ["https://a.example.com"]


def test_removes_duplicates_preserving_order(monkeypatch):
    settings = build_settings(
        monkeypatch,
        "https://b.example.com,https://a.example.com,https://b.example.com/",
    )
    assert settings.ALLOWED_ORIGINS == [
        "https://b.example.com",
        "https://a.example.com",
    ]


@pytest.mark.parametrize("raw", ["", "   ", ",", " , "])
def test_blank_values_yield_empty_list(monkeypatch, raw):
    """Un valor vacío no debe reventar el arranque, solo dejar la lista vacía."""
    assert build_settings(monkeypatch, raw).ALLOWED_ORIGINS == []


def test_malformed_json_yields_empty_list(monkeypatch):
    assert build_settings(monkeypatch, '["https://a.example.com"').ALLOWED_ORIGINS == []


def test_falls_back_to_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ALLOWED_ORIGINS == DEFAULT_ORIGINS
    assert "https://admin.geminislabs.com" in settings.ALLOWED_ORIGINS
    assert "http://localhost:5174" in settings.ALLOWED_ORIGINS
