"""Routing logic tests."""

from __future__ import annotations

from app.services.arena_data import Arena, Sector, get_arena
from app.services.routing import compute_shortest_path, path_distance


def test_same_start_and_goal_is_empty_path():
    assert compute_shortest_path(get_arena(), "gate_a", "gate_a") == []


def test_unknown_sector_returns_none():
    assert compute_shortest_path(get_arena(), "nowhere", "gate_a") is None


def test_disconnected_goal_returns_none():
    arena = Arena(
        name="t", fifa_name="t", city="t", capacity=1,
        sectors={
            "a": Sector("a", {"en": "A"}, "concourse", "x"),
            "b": Sector("b", {"en": "B"}, "concourse", "x"),
        },
        adjacency={"a": [], "b": []},
        amenities=[], crowd_base={}, crowd_sim={},
    )
    assert compute_shortest_path(arena, "a", "b") is None


def test_step_free_route_avoids_stairs_and_is_longer():
    arena = get_arena()
    default = compute_shortest_path(arena, "concourse_lower_sw", "concourse_upper_w")
    step_free = compute_shortest_path(arena, "concourse_lower_sw", "concourse_upper_w", step_free_only=True)
    assert any(link.means == "stairs" for link in default)
    assert step_free is not None and all(link.step_free for link in step_free)
    assert path_distance(step_free) > path_distance(default)
