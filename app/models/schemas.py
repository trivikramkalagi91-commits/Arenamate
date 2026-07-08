"""Pydantic request/response models and enums for ArenaMate."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Language(StrEnum):
    """Supported localization languages."""

    en = "en"
    es = "es"
    fr = "fr"


class AccessibilityNeed(StrEnum):
    """Supported fan accessibility needs."""

    wheelchair = "wheelchair"
    visual = "visual"
    hearing = "hearing"
    none = "none"


class DestinationIntent(StrEnum):
    """Fan destination intents."""

    restroom = "restroom"
    gate = "gate"
    seat = "seat"
    exit = "exit"
    first_aid = "first_aid"
    concession = "concession"
    guest_services = "guest_services"
    water = "water"
    sensory_room = "sensory_room"


class OccupancyLevel(StrEnum):
    """Occupancy/crowd levels at sectors."""

    low = "low"
    medium = "medium"
    high = "high"


class AccessibilityMode(StrEnum):
    """Accessibility formatting modes."""

    standard = "standard"
    screen_reader = "screen_reader"
    captioned = "captioned"


class UserContext(BaseModel):
    """User input payload schema."""

    model_config = ConfigDict(extra="forbid")

    language: Language = Language.en
    current_location: str = Field(..., min_length=1, max_length=40)
    destination_intent: DestinationIntent
    accessibility_needs: list[AccessibilityNeed] = Field(
        default_factory=lambda: [AccessibilityNeed.none]
    )
    ticket_section: str | None = Field(
        default=None, max_length=8, pattern=r"^[A-Za-z0-9\- ]{1,8}$"
    )
    minutes_to_kickoff: int = Field(..., ge=-120, le=1440)
    question: str | None = Field(default=None, max_length=280)

    @field_validator("current_location")
    @classmethod
    def _validate_sector_exists(cls, value: str) -> str:
        from app.services.arena_data import get_arena

        if value not in get_arena().sector_ids():
            raise ValueError(f"unknown sector id: {value!r}")
        return value

    @field_validator("accessibility_needs")
    @classmethod
    def _normalize_needs(cls, needs: list[AccessibilityNeed]) -> list[AccessibilityNeed]:
        unique = set(needs)
        if AccessibilityNeed.none in unique and len(unique) > 1:
            unique.discard(AccessibilityNeed.none)
        if not unique:
            unique = {AccessibilityNeed.none}
        return sorted(unique, key=lambda n: n.value)

    @field_validator("question")
    @classmethod
    def _sanitize_question(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.services.security import clean_user_input

        cleaned = clean_user_input(value)
        return cleaned or None


class PathStep(BaseModel):
    """Single step along calculated wayfinding route."""

    order: int
    from_sector: str
    to_sector: str
    means: str
    step_free: bool
    distance: int
    landmark: str | None = None
    instruction: str


class AmenityInfo(BaseModel):
    """Details of the resolved target venue amenity."""

    id: str
    name: str
    type: str
    sector: str
    accessible: bool
    landmark: str | None = None


class AnalysisOutcome(BaseModel):
    """Deterministic result computed before phrasing."""

    amenity: AmenityInfo
    path_steps: list[PathStep]
    occupancy_level: OccupancyLevel
    language: Language
    accessibility_mode: AccessibilityMode
    landmark_based: bool = False
    hurry: bool = False
    alternatives_note: str | None = None
    urgency: str | None = None


class GuideResponse(BaseModel):
    """Unified guide service response schema."""

    answer: str
    path_steps: list[PathStep]
    amenity: AmenityInfo
    occupancy_level: OccupancyLevel
    language: Language
    accessibility_mode: AccessibilityMode
    alternatives_note: str | None = None
    urgency: str | None = None
    used_llm: bool


class HealthResponse(BaseModel):
    """Status probe response schema."""

    status: str = "ok"
