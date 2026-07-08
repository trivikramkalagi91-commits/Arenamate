"""Phrasing tests covering English, Spanish, and French templates."""

from __future__ import annotations

from app.services.phrasing import (
    PhrasingContext,
    build_step_instruction,
    compile_response,
    get_alternatives_note,
    get_type_label,
    get_urgency_note,
)


def _ctx(**overrides) -> PhrasingContext:
    base = {
        "language": "en",
        "facility_name": "North-East Accessible Restroom",
        "facility_type": "accessible_restroom",
        "facility_landmark": "beside the elevator",
        "crowd_level": "low",
        "accessibility_mode": "standard",
        "landmark_based": False,
        "hurry": False,
        "alternative_type": None,
        "total_distance": 100,
        "step_count": 2,
    }
    base.update(overrides)
    return PhrasingContext(**base)


def test_compile_en_with_all_flags():
    out = compile_response(
        _ctx(
            landmark_based=True,
            accessibility_mode="captioned",
            hurry=True,
            alternative_type="restroom",
        )
    )
    assert "screen readers" in out
    assert "sensory space" in out
    assert "proceed quickly" in out
    assert "quieter" in out


def test_compile_en_already_at_location():
    out = compile_response(_ctx(step_count=0, facility_landmark=None))
    assert "already arrived" in out


def test_compile_fr_with_all_flags():
    out = compile_response(
        _ctx(
            language="fr",
            step_count=0,
            landmark_based=True,
            accessibility_mode="captioned",
            hurry=True,
            alternative_type="restroom",
        )
    )
    assert "Vous êtes déjà" in out
    assert "lecteurs d'écran" in out
    assert "salle sensorielle" in out
    assert "commence bientôt" in out


def test_urgency_note_localized():
    assert "faites vite" in get_urgency_note("fr")
    assert "haste" in get_urgency_note("en")


def test_alternatives_note_localized():
    assert "plus calme" in get_alternatives_note("concession", "fr")
    assert "quieter" in get_alternatives_note("concession", "en")


def test_step_instruction_fr_variants():
    final = build_step_instruction(
        "elevator", "Upper Concourse", "near the lobby", is_final=True,
        facility_name="Restroom", language="fr",
    )
    mid = build_step_instruction(
        "walk", "Lower Concourse", None, is_final=False, facility_name="Restroom", language="fr",
    )
    assert "ascenseur" in final.lower()
    assert "se trouve" in final
    assert mid.startswith("Marchez")
    assert "jusqu'à" in mid


def test_compile_es_with_all_flags():
    out = compile_response(
        _ctx(
            language="es",
            step_count=0,
            landmark_based=True,
            accessibility_mode="captioned",
            hurry=True,
            alternative_type="restroom",
        )
    )
    assert "Se dirige" in out
    assert "Ya ha llegado" in out
    assert "lectores de pantalla" in out
    assert "sala sensorial" in out
    assert "avance rápidamente" in out


def test_spanish_helpers():
    assert "dese prisa" in get_urgency_note("es")
    assert "más tranquila" in get_alternatives_note("concession", "es")
    step = build_step_instruction(
        "elevator", "Vestíbulo superior", "junto al ascensor", is_final=True,
        facility_name="Aseo", language="es",
    )
    assert step.startswith("Tome el ascensor")
    assert "donde encontrará" in step


def test_type_label_localized():
    assert get_type_label("restroom", "es") == "aseo"
    assert get_type_label("restroom", "fr") == "toilettes"
    assert get_type_label("mystery_type", "en") == "mystery type"
