"""Time-dependent crowd occupancy estimation for sectors.

Calculates the effective crowd congestion levels by applying simulated shifts to
base occupancy statistics depending on kick-off proximity.
"""

from __future__ import annotations

from app.services.arena_data import Arena

_LEVELS = ("low", "medium", "high")
_LEVEL_INDEX = {lvl: idx for idx, lvl in enumerate(_LEVELS)}

# Constants for default simulation parameters
_DEFAULT_PRE_MATCH_MINUTES = 30
_DEFAULT_IMMINENT_MINUTES = 10


def _clamp_level(index: int) -> str:
    """Clamp the computed index level to valid crowd levels ('low', 'medium', 'high').

    Args:
        index (int): The computed numeric level index.

    Returns:
        str: The clamped crowd level string value.
    """
    return _LEVELS[max(0, min(len(_LEVELS) - 1, index))]


def get_simulated_occupancy(arena: Arena, sector_id: str, minutes_to_kickoff: int | None) -> str:
    """Determine the crowd status ('low', 'medium', 'high') at the given sector.

    Applies simulated time surges to gate and concourse areas leading up to kick-off.

    Args:
        arena (Arena): The Arena in-memory database instance.
        sector_id (str): The sector ID to evaluate.
        minutes_to_kickoff (int | None): Minutes until game start. Positive if before, negative if in-play.

    Returns:
        str: The computed simulated occupancy level ('low', 'medium', or 'high').
    """
    base_idx = _LEVEL_INDEX.get(arena.base_crowd(sector_id), 0)
    if minutes_to_kickoff is None:
        return _clamp_level(base_idx)

    sim = arena.crowd_sim
    surge_types = set(sim.get("surge_types", []))
    sect_type = arena.sector_type(sector_id)
    offset = 0

    if sect_type in surge_types:
        pre_match = int(sim.get("pre_match_window_minutes", _DEFAULT_PRE_MATCH_MINUTES))
        imminent = int(sim.get("imminent_window_minutes", _DEFAULT_IMMINENT_MINUTES))

        if 0 <= minutes_to_kickoff <= imminent:
            offset += 2
        elif imminent < minutes_to_kickoff <= pre_match:
            offset += 1

    if minutes_to_kickoff < 0 and sect_type == "gate" and sim.get("in_play_gate_relief"):
        offset -= 1

    return _clamp_level(base_idx + offset)
