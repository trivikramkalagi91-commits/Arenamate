"""Unit tests for arena fixture loading and localization helper."""

from __future__ import annotations

from app.services.arena_data import get_arena, localized


def test_localized_fallback_chain():
    assert localized(None, "en") is None
    assert localized({}, "es") is None
    assert localized({"es": "Hola"}, "es") == "Hola"
    assert localized({"en": "Hello"}, "es") == "Hello"
    assert localized({"fr": "Bonjour"}, "es") == "Bonjour"


def test_sector_name_localized_and_defaults():
    arena = get_arena()
    assert arena.sector_name("gate_a", "es") == "Puerta A (suroeste)"
    assert arena.sector_name("gate_a", "fr") == "Porte A (sud-ouest)"
    assert arena.sector_name("nope", "en") == "nope"
