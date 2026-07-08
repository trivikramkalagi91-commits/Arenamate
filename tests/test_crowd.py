"""Crowd occupancy simulation tests."""

from __future__ import annotations

from app.services.arena_data import get_arena
from app.services.crowd import get_simulated_occupancy


def test_none_minutes_returns_base_level():
    arena = get_arena()
    assert get_simulated_occupancy(arena, "concourse_lower_sw", None) == "high"


def test_in_play_gate_relief():
    arena = get_arena()
    assert get_simulated_occupancy(arena, "gate_a", -10) == "low"


def test_surge_windows_escalate_gates():
    arena = get_arena()
    assert get_simulated_occupancy(arena, "gate_c", 5) == "high"
    assert get_simulated_occupancy(arena, "gate_c", 20) == "medium"
    assert get_simulated_occupancy(arena, "gate_c", 300) == "low"
