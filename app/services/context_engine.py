"""Wayfinding decision and routing engine.

Processes user context, calculates routes, and maps inputs to outcomes.
"""

from __future__ import annotations

from app.models.schemas import (
    AccessibilityMode,
    AccessibilityNeed,
    AmenityInfo,
    AnalysisOutcome,
    DestinationIntent,
    GuideResponse,
    OccupancyLevel,
    PathStep,
    UserContext,
)
from app.services import phrasing
from app.services.arena_data import Amenity, Arena, Link, localized
from app.services.crowd import get_simulated_occupancy
from app.services.llm import BasePhraser
from app.services.phrasing import PhrasingContext
from app.services.routing import compute_shortest_path, path_distance

# Proximity kickoff time limit parameter (minutes)
_IMMINENT_KICKOFF_MINUTES = 15

# Map destination intents to amenity categories
_INTENT_TO_TYPES: dict[DestinationIntent, set[str]] = {
    DestinationIntent.restroom: {"restroom", "accessible_restroom"},
    DestinationIntent.first_aid: {"first_aid"},
    DestinationIntent.concession: {"concession"},
    DestinationIntent.guest_services: {"guest_services"},
    DestinationIntent.water: {"water"},
    DestinationIntent.sensory_room: {"sensory_room"},
    DestinationIntent.exit: {"exit"},
    DestinationIntent.gate: {"gate"},
}

_SWAP_ELIGIBLE = {
    DestinationIntent.restroom,
    DestinationIntent.concession,
    DestinationIntent.water,
    DestinationIntent.guest_services,
    DestinationIntent.sensory_room,
    DestinationIntent.gate,
    DestinationIntent.exit,
}

_OCCUPANCY_RANK = {OccupancyLevel.low: 0, OccupancyLevel.medium: 1, OccupancyLevel.high: 2}
_HURRY_INTENTS = {DestinationIntent.gate, DestinationIntent.seat}


class PathNotFoundException(Exception):
    """Raised when no navigable path is found."""


def _to_amenity_info(amenity: Amenity, language: str) -> AmenityInfo:
    """Format parsed Amenity into public Pydantic model representation.

    Args:
        amenity (Amenity): Dataclass representing target amenity.
        language (str): Localized target language.

    Returns:
        AmenityInfo: Pydantic model representation of the Amenity.
    """
    return AmenityInfo(
        id=amenity.id,
        name=localized(amenity.names, language) or amenity.id,
        type=amenity.type,
        sector=amenity.sector,
        accessible=amenity.accessible,
        landmark=localized(amenity.landmarks, language),
    )


def _resolve_seat(ctx: UserContext, arena: Arena) -> Amenity:
    """Resolve seat amenity by checking the section digit.

    Args:
        ctx (UserContext): User wayfinding inputs context.
        arena (Arena): The current Arena in-memory database instance.

    Returns:
        Amenity: The resolved seat Amenity instance.

    Raises:
        PathNotFoundException: If seat fixture is missing in database.
    """
    sec = (ctx.ticket_section or "").strip()
    upper = bool(sec) and sec[0] in {"2", "3", "4"}
    target_id = "seat_upper" if upper else "seat_lower"
    for amenity in arena.amenities:
        if amenity.id == target_id:
            return amenity
    raise PathNotFoundException("seat amenity fixture is missing")


def _candidates_with_routes(
    ctx: UserContext, arena: Arena, types: set[str], *, accessible_only: bool, step_free: bool
) -> list[tuple[Amenity, list[Link], int]]:
    """Resolve candidate amenities with calculated paths.

    Args:
        ctx (UserContext): Input contexts.
        arena (Arena): The Arena database.
        types (set[str]): Candidate categories types.
        accessible_only (bool): Filters accessible-only.
        step_free (bool): Traversal link constraints.

    Returns:
        list[tuple[Amenity, list[Link], int]]: List of (Amenity, Path, Distance) sorted by distance.
    """
    candidates: list[tuple[Amenity, list[Link], int]] = []
    for amenity in arena.amenities_of_types(types, accessible_only=accessible_only):
        path = compute_shortest_path(arena, ctx.current_location, amenity.sector, step_free_only=step_free)
        if path is None:
            continue
        candidates.append((amenity, path, path_distance(path)))
    # Sort by path distance, then by ID
    candidates.sort(key=lambda item: (item[2], item[0].id))
    return candidates


def _build_path_steps(
    arena: Arena, start: str, path: list[Link], amenity: Amenity, language: str
) -> list[PathStep]:
    """Compile raw path links into formatted guide instructions.

    Args:
        arena (Arena): Current Arena DB.
        start (str): Start sector ID.
        path (list[Link]): Graph connection path links.
        amenity (Amenity): Target destination amenity.
        language (str): Locale language.

    Returns:
        list[PathStep]: Path instruction steps.
    """
    steps: list[PathStep] = []
    amenity_name = localized(amenity.names, language) or amenity.id
    node = start
    for idx, link in enumerate(path):
        is_final = idx == len(path) - 1
        landmark = localized(amenity.landmarks, language) if is_final else None
        steps.append(
            PathStep(
                order=idx + 1,
                from_sector=node,
                to_sector=link.to,
                means=link.means,
                step_free=link.step_free,
                distance=link.distance,
                landmark=landmark,
                instruction=phrasing.build_step_instruction(
                    link.means,
                    arena.sector_name(link.to, language),
                    landmark,
                    is_final=is_final,
                    facility_name=amenity_name,
                    language=language,
                ),
            )
        )
        node = link.to
    return steps


def build_decision(ctx: UserContext, arena: Arena) -> AnalysisOutcome:
    """Process wayfinding rules and return a structured AnalysisOutcome.

    Args:
        ctx (UserContext): User input contexts.
        arena (Arena): The Arena database singleton.

    Returns:
        AnalysisOutcome: Deterministic route decision results.

    Raises:
        PathNotFoundException: If no route exists to target.
    """
    needs = set(ctx.accessibility_needs)
    wheelchair = AccessibilityNeed.wheelchair in needs
    visual = AccessibilityNeed.visual in needs
    hearing = AccessibilityNeed.hearing in needs

    accessible_only = wheelchair or visual
    step_free = wheelchair or visual

    if visual:
        mode = AccessibilityMode.screen_reader
    elif hearing:
        mode = AccessibilityMode.captioned
    else:
        mode = AccessibilityMode.standard

    # Resolve target and path
    if ctx.destination_intent == DestinationIntent.seat:
        amenity = _resolve_seat(ctx, arena)
        path = compute_shortest_path(arena, ctx.current_location, amenity.sector, step_free_only=step_free)
        if path is None:
            raise PathNotFoundException("no accessible route to seat")
        alt_note: str | None = None
    else:
        types = _INTENT_TO_TYPES[ctx.destination_intent]
        candidates = _candidates_with_routes(
            ctx, arena, types, accessible_only=accessible_only, step_free=step_free
        )
        if not candidates:
            raise PathNotFoundException(f"no reachable facility for intent {ctx.destination_intent.value}")
        amenity, path, _ = candidates[0]
        amenity, path, alt_note = _maybe_swap_for_crowd(
            ctx, arena, amenity, path, candidates
        )

    occupancy = OccupancyLevel(get_simulated_occupancy(arena, amenity.sector, ctx.minutes_to_kickoff))
    hurry = ctx.minutes_to_kickoff < _IMMINENT_KICKOFF_MINUTES and ctx.destination_intent in _HURRY_INTENTS
    urgency = phrasing.get_urgency_note(ctx.language.value) if hurry else None

    path_steps = _build_path_steps(
        arena, ctx.current_location, path, amenity, ctx.language.value
    )

    return AnalysisOutcome(
        amenity=_to_amenity_info(amenity, ctx.language.value),
        path_steps=path_steps,
        occupancy_level=occupancy,
        language=ctx.language,
        accessibility_mode=mode,
        landmark_based=visual,
        hurry=hurry,
        alternatives_note=alt_note,
        urgency=urgency,
    )


def _maybe_swap_for_crowd(
    ctx: UserContext,
    arena: Arena,
    amenity: Amenity,
    path: list[Link],
    candidates: list[tuple[Amenity, list[Link], int]],
) -> tuple[Amenity, list[Link], str | None]:
    """Swap to a quieter alternative amenity if the nearest is crowded.

    Args:
        ctx (UserContext): User contexts.
        arena (Arena): The Arena database.
        amenity (Amenity): Current resolved nearest amenity.
        path (list[Link]): Connection link path.
        candidates (list[tuple[Amenity, list[Link], int]]): All candidate options list.

    Returns:
        tuple[Amenity, list[Link], str | None]: (amenity, path, warning_note).
    """
    if ctx.destination_intent not in _SWAP_ELIGIBLE:
        return amenity, path, None

    primary_occupancy = OccupancyLevel(get_simulated_occupancy(arena, amenity.sector, ctx.minutes_to_kickoff))
    if primary_occupancy != OccupancyLevel.high:
        return amenity, path, None

    alternatives: list[tuple[int, int, str, Amenity, list[Link]]] = []
    for cand, cand_path, cand_dist in candidates:
        if cand.id == amenity.id:
            continue
        cand_occ = OccupancyLevel(get_simulated_occupancy(arena, cand.sector, ctx.minutes_to_kickoff))
        if cand_occ == OccupancyLevel.high:
            continue
        alternatives.append((_OCCUPANCY_RANK[cand_occ], cand_dist, cand.id, cand, cand_path))

    if not alternatives:
        return amenity, path, None

    # Sort deterministically: quietest first, then nearest, then by ID
    alternatives.sort(key=lambda a: (a[0], a[1], a[2]))
    _, _, _, alt_amenity, alt_path = alternatives[0]
    note = phrasing.get_alternatives_note(alt_amenity.type, ctx.language.value)
    return alt_amenity, alt_path, note


async def run_guide(ctx: UserContext, arena: Arena, phraser: BasePhraser) -> GuideResponse:
    """Compute structural decision and phrase response.

    Args:
        ctx (UserContext): User query inputs.
        arena (Arena): Arena database singleton.
        phraser (BasePhraser): Active phrasing client.

    Returns:
        GuideResponse: Complete response payload.
    """
    decision = build_decision(ctx, arena)

    phrasing_ctx = PhrasingContext(
        language=decision.language.value,
        facility_name=decision.amenity.name,
        facility_type=decision.amenity.type,
        facility_landmark=decision.amenity.landmark,
        crowd_level=decision.occupancy_level.value,
        accessibility_mode=decision.accessibility_mode.value,
        landmark_based=decision.landmark_based,
        hurry=decision.hurry,
        alternative_type=decision.amenity.type if decision.alternatives_note else None,
        total_distance=sum(step.distance for step in decision.path_steps),
        step_count=len(decision.path_steps),
    )

    if ctx.question:
        answer = await phraser.phrase(phrasing_ctx, ctx.question)
        used_llm = phraser.is_live
    else:
        answer = phrasing.compile_response(phrasing_ctx)
        used_llm = False

    return GuideResponse(
        answer=answer,
        path_steps=decision.path_steps,
        amenity=decision.amenity,
        occupancy_level=decision.occupancy_level,
        language=decision.language,
        accessibility_mode=decision.accessibility_mode,
        alternatives_note=decision.alternatives_note,
        urgency=decision.urgency,
        used_llm=used_llm,
    )
