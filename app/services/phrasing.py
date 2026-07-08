"""Phrasing engine for ArenaMate.

Generates localized phrasing (English, Spanish, and French) from decision facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

_DEFAULT_LANG = "en"

# Navigation directions by means of travel
_MEANS: dict[str, dict[str, str]] = {
    "en": {"walk": "walk", "ramp": "take the ramp", "elevator": "take the elevator",
           "stairs": "take the stairs"},
    "es": {"walk": "camine", "ramp": "tome la rampa", "elevator": "tome el ascensor",
           "stairs": "suba por las escaleras"},
    "fr": {"walk": "marchez", "ramp": "empruntez la rampe", "elevator": "prenez l'ascenseur",
           "stairs": "prenez les escaliers"},
}

_CROWD_WORD: dict[str, dict[str, str]] = {
    "en": {"low": "low", "medium": "moderate", "high": "high"},
    "es": {"low": "baja", "medium": "moderada", "high": "alta"},
    "fr": {"low": "faible", "medium": "modérée", "high": "élevée"},
}

_TYPE_LABEL: dict[str, dict[str, str]] = {
    "en": {"restroom": "restroom", "accessible_restroom": "accessible restroom",
           "first_aid": "first aid station", "concession": "concession stand",
           "guest_services": "guest services desk", "water": "water refill station",
           "sensory_room": "sensory room", "exit": "exit", "gate": "gate",
           "seat": "seat", "elevator": "elevator"},
    "es": {"restroom": "aseo", "accessible_restroom": "aseo accesible",
           "first_aid": "puesto de primeros auxilios", "concession": "puesto de comida",
           "guest_services": "punto de atención", "water": "fuente de agua",
           "sensory_room": "sala sensorial", "exit": "salida", "gate": "puerta",
           "seat": "asiento", "elevator": "ascensor"},
    "fr": {"restroom": "toilettes", "accessible_restroom": "toilettes accessibles",
           "first_aid": "poste de premiers secours", "concession": "point de restauration",
           "guest_services": "comptoir d'accueil", "water": "point d'eau",
           "sensory_room": "salle sensorielle", "exit": "sortie", "gate": "porte",
           "seat": "place", "elevator": "ascenseur"},
}

# Step-by-step connection instructions
_STEP: dict[str, dict[str, str]] = {
    "en": {"final": "{verb} to {to}, where you will find the {name}{lm}.", "mid": "{verb} to {to}."},
    "es": {"final": "{verb} hasta {to}, donde encontrará el/la {name}{lm}.", "mid": "{verb} hasta {to}."},
    "fr": {"final": "{verb} jusqu'à {to}, où se trouve {name}{lm}.", "mid": "{verb} jusqu'à {to}."},
}

_ALT_NOTE: dict[str, str] = {
    "en": "The closest {label} is currently busy, so we recommend this quieter option.",
    "es": "El {label} más cercano está concurrido; se sugiere una alternativa más tranquila.",
    "fr": "Le/la {label} le/la plus proche est bondé(e) : une option plus calme est proposée.",
}

_URGENCY: dict[str, str] = {
    "en": "Kickoff is in less than 15 minutes — please make haste.",
    "es": "Comienzo en menos de 15 minutos: dese prisa.",
    "fr": "Coup d'envoi dans moins de 15 minutes — faites vite.",
}

# prose composition pieces
_ANSWER: dict[str, dict[str, str]] = {
    "en": {
        "dest": "You are headed to {name}{lm}.",
        "here": "You have already arrived at this location.",
        "route": "Please use the {n}-step path below (approx. {d} m).",
        "crowd": "The crowd density there is currently {c}.",
        "landmark": "Landmarks are included in these directions for screen readers.",
        "captioned": "Look out for visual signs along the path; a quiet sensory space is available if needed.",
        "hurry": "The game starts shortly; please proceed quickly.",
    },
    "es": {
        "dest": "Se dirige a {name}{lm}.",
        "here": "Ya ha llegado a esta ubicación.",
        "route": "Siga las {n} indicaciones siguientes (aprox. {d} m).",
        "crowd": "La densidad de afluencia allí es actualmente {c}.",
        "landmark": "Estas direcciones usan puntos de referencia optimizados para lectores de pantalla.",
        "captioned": "Siga los carteles visuales en el trayecto; dispone de una sala sensorial tranquila si la necesita.",
        "hurry": "El partido empieza pronto: avance rápidamente.",
    },
    "fr": {
        "dest": "Vous vous dirigez vers {name}{lm}.",
        "here": "Vous êtes déjà sur place.",
        "route": "Veuillez suivre le parcours en {n} étape(s) (environ {d} m).",
        "crowd": "La densité de la foule y est actuellement {c}.",
        "landmark": "Ces indications incluent des repères visuels adaptés aux lecteurs d'écran.",
        "captioned": "Suivez la signalisation visuelle sur le trajet ; une salle sensorielle calme est disponible.",
        "hurry": "Le match commence bientôt — avancez rapidement.",
    },
}


def _lang(language: str) -> str:
    """Standardize language key to fallback en if unsupported.

    Args:
        language (str): Requested language code.

    Returns:
        str: Valid supported language key.
    """
    return language if language in _MEANS else _DEFAULT_LANG


def _cap(text: str) -> str:
    """Capitalize first character of text.

    Args:
        text (str): Input text string.

    Returns:
        str: Capitalized text string.
    """
    return text[:1].upper() + text[1:] if text else text


def get_type_label(facility_type: str, language: str) -> str:
    """Get localized label for an amenity category type.

    Args:
        facility_type (str): The amenity category identifier.
        language (str): The target language.

    Returns:
        str: Localized label string.
    """
    lang = _lang(language)
    return _TYPE_LABEL[lang].get(facility_type, facility_type.replace("_", " "))


def build_step_instruction(
    means: str,
    to_name: str,
    landmark: str | None,
    *,
    is_final: bool,
    facility_name: str,
    language: str,
) -> str:
    """Compose step-by-step connection wayfinding instructions.

    Args:
        means (str): Connection travel type.
        to_name (str): Localized target sector name.
        landmark (str | None): Target landmark detail, if applicable.
        is_final (bool): True if final target, False otherwise.
        facility_name (str): Name of destination amenity.
        language (str): Output language code.

    Returns:
        str: Localized connecting instruction text.
    """
    lang = _lang(language)
    verb = _cap(_MEANS[lang].get(means, _MEANS[lang]["walk"]))
    lm = f" ({landmark})" if (is_final and landmark) else ""
    template = _STEP[lang]["final" if is_final else "mid"]
    return template.format(verb=verb, to=to_name, name=facility_name, lm=lm)


def get_alternatives_note(facility_type: str, language: str) -> str:
    """Compose localized warning notes for rerouted amenities.

    Args:
        facility_type (str): Category type of amenity.
        language (str): Target language.

    Returns:
        str: Localized notification text.
    """
    lang = _lang(language)
    return _ALT_NOTE[lang].format(label=get_type_label(facility_type, lang))


def get_urgency_note(language: str) -> str:
    """Get localized kickoff proximity urgency alert message.

    Args:
        language (str): Target language.

    Returns:
        str: Localized urgency alert message.
    """
    return _URGENCY[_lang(language)]


@dataclass(frozen=True)
class PhrasingContext:
    """Details injected into the phraser engine.

    Attributes:
        language (str): Destination language code.
        facility_name (str): Destination amenity name.
        facility_type (str): Proximity target amenity type.
        facility_landmark (str | None): Target landmark details.
        crowd_level (str): Simulated occupancy level.
        accessibility_mode (str): Output formatting mode.
        landmark_based (bool): If True, landmarks will be emphasized.
        hurry (bool): True if kick-off time is critical.
        alternative_type (str | None): Previous closer target category if swapped.
        total_distance (int): Path length in meters.
        step_count (int): Steps in route.
    """

    language: str
    facility_name: str
    facility_type: str
    facility_landmark: str | None
    crowd_level: str
    accessibility_mode: str
    landmark_based: bool
    hurry: bool
    alternative_type: str | None
    total_distance: int
    step_count: int


@lru_cache(maxsize=256)
def compile_response(ctx: PhrasingContext) -> str:
    """Compose paragraph describing navigation directions.

    Args:
        ctx (PhrasingContext): The phrasing facts context.

    Returns:
        str: Compiled paragraph text.
    """
    lang = _lang(ctx.language)
    a = _ANSWER[lang]
    c_word = _CROWD_WORD[lang][ctx.crowd_level]
    dest_lm = f" ({ctx.facility_landmark})" if ctx.facility_landmark else ""

    parts = [a["dest"].format(name=ctx.facility_name, lm=dest_lm)]
    if ctx.step_count == 0:
        parts.append(a["here"])
    else:
        parts.append(a["route"].format(n=ctx.step_count, d=ctx.total_distance))
    parts.append(a["crowd"].format(c=c_word))
    if ctx.alternative_type:
        parts.append(get_alternatives_note(ctx.alternative_type, lang))
    if ctx.landmark_based:
        parts.append(a["landmark"])
    if ctx.accessibility_mode == "captioned":
        parts.append(a["captioned"])
    if ctx.hurry:
        parts.append(a["hurry"])
    return " ".join(parts)
