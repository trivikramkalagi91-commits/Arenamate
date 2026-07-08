"""Wayfinding decision and routing rules tests."""

from __future__ import annotations

import pytest

from app.models.schemas import (
    AccessibilityMode,
    OccupancyLevel,
    UserContext,
)
from app.services.arena_data import Amenity, Arena, Sector, get_arena
from app.services.context_engine import PathNotFoundException, build_decision


def _mini_arena(amenities: list[Amenity]) -> Arena:
    """A minimal single-sector arena with empty linkages."""
    return Arena(
        name="t", fifa_name="t", city="t", capacity=1,
        sectors={"z1": Sector("z1", {"en": "Z1"}, "concourse", "x")},
        adjacency={"z1": []},
        amenities=amenities,
        crowd_base={"z1": "low"},
        crowd_sim={},
    )


def _ctx(**overrides) -> UserContext:
    base = {
        "language": "en",
        "current_location": "gate_a",
        "destination_intent": "restroom",
        "minutes_to_kickoff": 60,
    }
    base.update(overrides)
    return UserContext(**base)


def _decide(**overrides):
    base = {
        "language": "en",
        "current_location": "concourse_lower_sw",
        "destination_intent": "restroom",
        "minutes_to_kickoff": 60,
    }
    base.update(overrides)
    return build_decision(UserContext(**base), get_arena())


def test_wheelchair_gets_accessible_amenity_and_step_free_path():
    decision = _decide(accessibility_needs=["wheelchair"])
    assert decision.amenity.accessible is True
    assert decision.path_steps, "expected path steps"
    assert all(step.step_free for step in decision.path_steps)


def test_visual_need_sets_landmark_and_screen_reader_mode():
    decision = _decide(accessibility_needs=["visual"])
    assert decision.landmark_based is True
    assert decision.accessibility_mode is AccessibilityMode.screen_reader
    assert decision.amenity.accessible is True
    assert decision.path_steps[-1].landmark


def test_hearing_need_sets_captioned_mode():
    decision = _decide(accessibility_needs=["hearing"])
    assert decision.accessibility_mode is AccessibilityMode.captioned


def test_imminent_kickoff_triggers_urgency_for_gate():
    hurried = _decide(destination_intent="gate", current_location="concourse_upper_w",
                      minutes_to_kickoff=10)
    assert hurried.hurry is True
    assert hurried.urgency is not None

    relaxed = _decide(destination_intent="gate", current_location="concourse_upper_w",
                      minutes_to_kickoff=90)
    assert relaxed.hurry is False
    assert relaxed.urgency is None


def test_high_crowd_suggests_quieter_alternative():
    decision = _decide(destination_intent="concession", current_location="concourse_lower_sw",
                       minutes_to_kickoff=120)
    assert decision.alternatives_note is not None
    assert decision.occupancy_level is not OccupancyLevel.high
    assert decision.amenity.id != "concession_sw"


def test_first_aid_intent_never_swaps_for_crowd():
    decision = _decide(destination_intent="first_aid", current_location="concourse_lower_sw",
                       minutes_to_kickoff=5)
    assert decision.alternatives_note is None
    assert decision.amenity.type == "first_aid"


def test_seat_resolved_from_ticket_section():
    lower = _decide(destination_intent="seat", ticket_section="134")
    assert lower.amenity.id == "seat_lower"
    upper = _decide(destination_intent="seat", ticket_section="332")
    assert upper.amenity.id == "seat_upper"


def test_missing_seat_fixture_raises_route_not_found():
    with pytest.raises(PathNotFoundException):
        build_decision(_ctx(destination_intent="seat"), _mini_arena([]))


def test_unreachable_seat_raises_route_not_found():
    seat = Amenity("seat_lower", {"en": "Seat"}, "seat", "z1", True, None)
    with pytest.raises(PathNotFoundException):
        build_decision(_ctx(destination_intent="seat"), _mini_arena([seat]))


def test_no_reachable_facility_raises_route_not_found():
    restroom = Amenity("r1", {"en": "R"}, "restroom", "z1", False, None)
    with pytest.raises(PathNotFoundException):
        build_decision(_ctx(destination_intent="restroom"), _mini_arena([restroom]))


def test_default_route_may_use_stairs_but_accessible_route_never_does():
    default = _decide(destination_intent="restroom", current_location="concourse_lower_sw")
    accessible = _decide(destination_intent="restroom",
                         current_location="concourse_lower_sw",
                         accessibility_needs=["wheelchair"])
    assert all(step.step_free for step in accessible.path_steps)
    assert default.amenity.id != accessible.amenity.id
