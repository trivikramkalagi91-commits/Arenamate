"""Arena data parsing and accessor utility.

Reads arena.json, amenities.json, and crowd.json, and hosts them in an in-memory graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

I18n = dict[str, str]
_DEFAULT_LANG = "en"


def localized(mapping: I18n | None, language: str) -> str | None:
    """Resolve localization with a fallback scheme.

    Checks requested language, falls back to English, then to any available translation.

    Args:
        mapping (I18n | None): The localized text dictionary.
        language (str): The requested language code (e.g. 'en', 'es', 'fr').

    Returns:
        str | None: The resolved localized string, or None if mapping is empty/None.
    """
    if not mapping:
        return None
    return mapping.get(language) or mapping.get(_DEFAULT_LANG) or next(iter(mapping.values()))


@dataclass
class Sector:
    """A navigable sector node in the arena graph.

    Attributes:
        id (str): Unique sector ID.
        names (I18n): Localized names dictionary.
        type (str): Sector category type (e.g. "gate", "concourse", "seating").
        level (str): Venue level (e.g. "ground", "lower", "upper").
    """

    id: str
    names: I18n
    type: str
    level: str


@dataclass(frozen=True)
class Link:
    """A connection link between two sectors.

    Attributes:
        to (str): Target sector ID connected to.
        means (str): Proximity transit method (e.g. "walk", "ramp", "elevator", "stairs").
        step_free (bool): True if the connection is wheelchair accessible.
        distance (int): Distance between sectors in meters.
    """

    to: str
    means: str
    step_free: bool
    distance: int


@dataclass
class Amenity:
    """A point of interest (restroom, first aid, concession, gate, seat, ...).

    Attributes:
        id (str): Unique amenity ID.
        names (I18n): Localized names dictionary.
        type (str): Amenity category (e.g. "restroom", "concession", "first_aid").
        sector (str): The sector ID where this amenity is located.
        accessible (bool): True if the amenity itself is wheelchair accessible.
        landmarks (I18n | None): Optional landmarks mapping for wayfinding guidance.
    """

    id: str
    names: I18n
    type: str
    sector: str
    accessible: bool
    landmarks: I18n | None = None


@dataclass
class Arena:
    """Complete Arena representation in memory.

    Attributes:
        name (str): Arena name.
        fifa_name (str): FIFA tournament name.
        city (str): Location city.
        capacity (int): Seating capacity.
        sectors (dict[str, Sector]): Sectors dictionary mapping ID to Sector instance.
        adjacency (dict[str, list[Link]]): Graph adjacency lists mapping sector ID to connections.
        amenities (list[Amenity]): List of all amenities.
        crowd_base (dict[str, str]): Base crowd levels mapping sector ID to level.
        crowd_sim (dict[str, Any]): Crowd simulation configurations.
    """

    name: str
    fifa_name: str
    city: str
    capacity: int
    sectors: dict[str, Sector]
    adjacency: dict[str, list[Link]]
    amenities: list[Amenity]
    crowd_base: dict[str, str]
    crowd_sim: dict[str, Any] = field(default_factory=dict)

    def sector_ids(self) -> frozenset[str]:
        """All valid sector ids.

        Returns:
            frozenset[str]: Frozenset containing all sector IDs.
        """
        return frozenset(self.sectors)

    def sector_name(self, sector_id: str, language: str = _DEFAULT_LANG) -> str:
        """Resolve localized name for a sector.

        Args:
            sector_id (str): The sector ID.
            language (str): Requested language code. Defaults to "en".

        Returns:
            str: Localized name, or the ID itself as fallback.
        """
        sec = self.sectors.get(sector_id)
        return (localized(sec.names, language) or sector_id) if sec else sector_id

    def sector_type(self, sector_id: str) -> str:
        """Get type category for a sector.

        Args:
            sector_id (str): The sector ID.

        Returns:
            str: Sector type category, or empty string if sector is unknown.
        """
        sec = self.sectors.get(sector_id)
        return sec.type if sec else ""

    def neighbors(self, sector_id: str) -> list[Link]:
        """Get connecting links of a sector.

        Args:
            sector_id (str): The sector ID.

        Returns:
            list[Link]: List of Link connections.
        """
        return self.adjacency.get(sector_id, [])

    def amenities_of_types(
        self, types: set[str], *, accessible_only: bool = False
    ) -> list[Amenity]:
        """Get amenities matching any of the specified types.

        Args:
            types (set[str]): Set of allowed amenity types.
            accessible_only (bool): If True, filters out non-accessible amenities. Defaults to False.

        Returns:
            list[Amenity]: List of matching Amenity instances.
        """
        return [
            a
            for a in self.amenities
            if a.type in types and (a.accessible or not accessible_only)
        ]

    def base_crowd(self, sector_id: str) -> str:
        """Get base crowd level for a sector.

        Args:
            sector_id (str): The sector ID.

        Returns:
            str: Base crowd level code, defaulting to "low" if unknown.
        """
        return self.crowd_base.get(sector_id, "low")


def _read_json(filename: str) -> dict[str, Any]:
    """Read a JSON data fixture.

    Args:
        filename (str): Name of the JSON file in app/data.

    Returns:
        dict[str, Any]: Parsed JSON dictionary content.
    """
    with (_DATA_DIR / filename).open(encoding="utf-8") as fh:
        return json.load(fh)


def _build_arena() -> Arena:
    """Parse JSON fixtures and build in-memory Arena instance.

    Returns:
        Arena: The constructed Arena instance.
    """
    arena_raw = _read_json("arena.json")
    amenities_raw = _read_json("amenities.json")
    crowd_raw = _read_json("crowd.json")

    sectors = {
        s["id"]: Sector(id=s["id"], names=s["name"], type=s["type"], level=s["level"])
        for s in arena_raw["sectors"]
    }

    adjacency: dict[str, list[Link]] = {sid: [] for sid in sectors}
    for e in arena_raw["links"]:
        src, dst = e["from"], e["to"]
        adjacency[src].append(
            Link(to=dst, means=e["means"], step_free=e["step_free"], distance=e["distance"])
        )
        adjacency[dst].append(
            Link(to=src, means=e["means"], step_free=e["step_free"], distance=e["distance"])
        )

    amenities = [
        Amenity(
            id=a["id"],
            names=a["name"],
            type=a["type"],
            sector=a["sector"],
            accessible=a["accessible"],
            landmarks=a.get("landmark"),
        )
        for a in amenities_raw["amenities"]
    ]

    meta = arena_raw["arena"]
    return Arena(
        name=meta["name"],
        fifa_name=meta["fifa_name"],
        city=meta["city"],
        capacity=meta["capacity"],
        sectors=sectors,
        adjacency=adjacency,
        amenities=amenities,
        crowd_base=dict(crowd_raw["base_levels"]),
        crowd_sim=dict(crowd_raw.get("sim_settings", {})),
    )


@lru_cache(maxsize=1)
def get_arena() -> Arena:
    """Return process-wide Arena singleton.

    Returns:
        Arena: The cached Arena singleton instance.
    """
    return _build_arena()
