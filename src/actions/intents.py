import re
from dataclasses import replace
from typing import Collection, Sequence

from src.actions.embedding import Embedder, best_match
from src.actions.models import SCENES, Scene
from src.handlers.lights import Light, State

DEFAULT_BRIGHTNESS = 50
SCENE_THRESHOLD = 0.4

OFF_PATTERN = re.compile(
    r"\b(turn|switch)\b.*\boff\b"
    r"|\bschalte\b.*\baus\b"
    r"|\bmach\b.*\baus\b"
    r"|\bmache\b.*\baus\b"
    r"|\b(?:licht|lampe|light|lamp|alle[sn]?\s+(?:licht(?:er)?|lampe))\s+(?:off|aus)\b"
    r"|\b(?:deactivate|ausschalten|abschalten)\b",
    re.IGNORECASE,
)
ON_PATTERN = re.compile(
    r"\b(turn|switch)\b.*\bon\b"
    r"|\bschalte\b.*\b(an|ein)\b"
    r"|\bmach\b.*\ban\b"
    r"|\bmache\b.*\ban\b"
    r"|\b(?:licht|lampe|light|lamp|alle[sn]?\s+(?:licht(?:er)?|lampe))\s+(?:on|an|ein)\b"
    r"|\b(?:activate|einschalten|anschalten)\b",
    re.IGNORECASE,
)
DIM_DOWN_PATTERN = re.compile(
    r"\b(dim|dimmer|darker|dunkler|weniger|less|reduce|niedriger)\b",
    re.IGNORECASE,
)
DIM_UP_PATTERN = re.compile(
    r"\b(bright|brighter|heller|mehr|more|increase|aufhellen)\b",
    re.IGNORECASE,
)

COLOR_PATTERNS: tuple[tuple[re.Pattern, State], ...] = (
    (re.compile(r"\b(red|rot)\b", re.IGNORECASE), State(on=True, hue=0, sat=100, bri=80)),
    (re.compile(r"\b(orange)\b", re.IGNORECASE), State(on=True, hue=30, sat=100, bri=80)),
    (re.compile(r"\b(yellow|gelb)\b", re.IGNORECASE), State(on=True, hue=60, sat=100, bri=80)),
    (re.compile(r"\b(green|grün|gruen)\b", re.IGNORECASE), State(on=True, hue=120, sat=100, bri=70)),
    (re.compile(r"\b(blue|blau)\b", re.IGNORECASE), State(on=True, hue=240, sat=100, bri=70)),
    (re.compile(r"\b(purple|lila|violett)\b", re.IGNORECASE), State(on=True, hue=280, sat=100, bri=70)),
    (re.compile(r"\b(pink|rosa)\b", re.IGNORECASE), State(on=True, hue=330, sat=80, bri=80)),
    (re.compile(r"\b(white|weiß|weiss)\b", re.IGNORECASE), State(on=True, hue=0, sat=0, bri=100)),
    (re.compile(r"\b(warm)\b", re.IGNORECASE), State(on=True, hue=25, sat=70, bri=70)),
    (re.compile(r"\b(cold|kalt|kühles|kuehles)\b", re.IGNORECASE), State(on=True, hue=210, sat=60, bri=70)),
)


def _apply_state(lights: Collection[Light], state: State) -> list[Light]:
    return [replace(light, state=state) for light in lights]


def apply_intent_off(
    instruction: str,
    current_state: Collection[Light] | None,
) -> Collection[Light] | None:
    if not current_state:
        return None
    if OFF_PATTERN.search(instruction.lower()):
        return _apply_state(current_state, State(on=False))
    return None


def apply_intent_scene(
    instruction: str,
    current_state: Collection[Light] | None,
    scenes: Sequence[Scene],
    embedder: Embedder,
    threshold: float = SCENE_THRESHOLD,
) -> Collection[Light] | None:
    if not current_state:
        return None
    normalized = instruction.lower()
    candidates = [scene for scene in scenes if scene.pattern and scene.pattern.search(normalized)]
    if not candidates:
        return None
    matches = best_match(candidates, embedder, instruction, top_n=1, threshold=threshold)
    if not matches:
        return None
    return _apply_state(current_state, matches[0].state)


def apply_intent_individual(
    instruction: str,
    current_state: Collection[Light] | None,
) -> Collection[Light] | None:
    if not current_state:
        return None
    normalized = instruction.lower()
    if DIM_DOWN_PATTERN.search(normalized):
        return [replace(light, state=_dimmed(light.state, factor=0.5)) for light in current_state]
    if DIM_UP_PATTERN.search(normalized):
        return [replace(light, state=_dimmed(light.state, factor=1.5)) for light in current_state]
    for color_pattern, color_state in COLOR_PATTERNS:
        if color_pattern.search(normalized):
            return _apply_state(current_state, color_state)
    if ON_PATTERN.search(normalized):
        return _apply_state(current_state, State(on=True))
    return None


def _dimmed(state: State, factor: float) -> State:
    current = state.bri if state.bri is not None else DEFAULT_BRIGHTNESS
    if factor < 1.0:
        bri = max(0, round(current * factor))
    else:
        bri = min(100, round(current * factor))
    return State(on=True, bri=bri)


def apply_intent(
    instruction: str,
    affected_lights: Collection[Light],
    embedder: Embedder,
) -> Collection[Light] | None:
    if (result := apply_intent_off(instruction, affected_lights)) is not None:
        return result
    if (result := apply_intent_scene(instruction, affected_lights, SCENES, embedder)) is not None:
        return result
    return apply_intent_individual(instruction, affected_lights)
