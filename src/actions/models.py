from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.handlers.lights import LightState


@dataclass(frozen=True, slots=True)
class Describable:
    name: str
    descriptions: tuple[str, ...]

    def __str__(self):
        return self.name


@dataclass(frozen=True, slots=True)
class Intent(Describable):
    pattern: re.Pattern | None = None
    nested: tuple[Intent, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Scene(Describable):
    """
    Candidates:
    MOVIE_NIGHT
    SUNSET
    MORNING_MOOD
    WORK
    COZY
    CALM
    SLEEPING
    """


@dataclass(frozen=True, slots=True)
class Light(Describable):
    id: str
    state: LightState


def as_lights(list_states: list[LightState]) -> list[Light]:
    result = []
    for state in list_states:
        light = Light(id=state.id, name=state.name, descriptions=_generate_light_descriptions(state.name), state=state)
        result.append(light)
    return result


def _generate_light_descriptions(name: str) -> tuple[str, ...]:
    normalized = name.lower().strip()
    descriptions = [
        normalized,
        f"{normalized} light",
        f"{normalized} lamp",
    ]

    words = normalized.split()
    if len(words) > 1:
        reversed_name = " ".join(reversed(words))
        descriptions.extend(
            [
                reversed_name,
                f"{reversed_name} light",
                f"{reversed_name} lamp",
            ]
        )
    return tuple(dict.fromkeys(descriptions))


OFF_PATTERN = re.compile(
    r"\b(turn|switch)\b.*\boff\b"
    r"|\bschalte\b.*\baus\b"
    r"|\bmach\b.*\baus\b"
    r"|\bmache\b.*\baus\b"
    r"|\b(?:licht|lampe|light|lamp|alle(?:s|n)?\s+(?:licht(?:er)?|lampe))\s+(?:off|aus)\b"
    r"|\b(?:deactivate|ausschalten|abschalten)\b",
    re.IGNORECASE,
)
ON_PATTERN = re.compile(
    r"\b(turn|switch)\b.*\bon\b"
    r"|\bschalte\b.*\b(an|ein)\b"
    r"|\bmach\b.*\ban\b"
    r"|\bmache\b.*\ban\b"
    r"|\b(?:licht|lampe|light|lamp|alle(?:s|n)?\s+(?:licht(?:er)?|lampe))\s+(?:on|an|ein)\b"
    r"|\b(?:activate|einschalten|anschalten)\b",
    re.IGNORECASE,
)

INTENTS: list[Intent] = [
    Intent(
        name="off",
        descriptions = (),
        pattern=OFF_PATTERN,
    ),
    Intent(
        name="on",
        descriptions=(),
        pattern=ON_PATTERN,
        nested=(
            Intent(
                name="brightness",
                descriptions=(
                    "About slightly changing the intensity of light state: Dimming or increasing power.",
                    "Make the light slightly brighter or darker.",
                    "Adjust the brightness",
                    "Increase or decrease the intensity of on or multiple lights",
                )
            ),
            Intent(
                name="color",
                descriptions=(
                    "About changing the color and chromatic appearance of one or multiple lights.",
                    "Set the color or heu of one or multiple lights to a specific color.",
                    "Set the warmth of one or multiple lights to a specific value.",
                    "Set the coldness of one or multiple lights to a specific value.",
                ),
            ),
            Intent(
                name="scene",
                descriptions=(
                    "Create an directly specified atmosphere with one or multiple lights",
                    "Set the lights to underline and support a specific intent like watching a movie, going to sleep, studying or cleaning",
                    "Modify the lights to achieve a very specific lighting mood",
                    "Set up lights to resemble a feeling like coziness, coldness, focus or warmth",
                ),
            ),
        )
    ),
]

SCENES: list[Scene] = [
    Scene(
        name="movie_night",
        descriptions=(
            "Dark cinematic lighting for watching movies. A cinema atmosphere with comfortable low lighting. Relaxing evening lighting for watching a film. Dim ambient lights suitable for television or movies.",
            "Dunkles kinomäßiges Licht fürs Film schauen. Eine Kinoatmosphäre mit angenehmer schwacher Beleuchtung. Entspannte Abendbeleuchtung für einen Filmabend. Gedämpftes Umgebungslicht geeignet für Fernsehen oder Filme.",
        ),
    ),
    Scene(
        name="sunset",
        descriptions=(
            "Warm orange evening lighting. Soft golden light similar to sunset. Relaxing warm colors for an evening atmosphere. Orange and warm ambient lighting.",
            "Warmes oranges Abendlicht. Sanftes goldenes Licht ähnlich wie bei Sonnenuntergang. Entspannte warme Farben für eine Abendatmosphäre. Orange und warme Umgebungsbeleuchtung.",
        ),
    ),
    Scene(
        name="morning_mood",
        descriptions=(
            "Bright refreshing light for the morning. Wake up lighting that feels natural and energizing. Clear bright lighting for starting the day. Fresh daylight-like room illumination.",
            "Helles erfrischendes Licht für den Morgen. Weckbeleuchtung die sich natürlich und belebend anfühlt. Klares helles Licht zum Tagesbeginn. Frische tageslichtähnliche Raumbeleuchtung.",
        ),
    ),
    Scene(
        name="work",
        descriptions=(
            "Focused lighting for working or studying. Bright practical lighting. Clear task lighting for productivity. Office-style illumination.",
            "Konzentriertes Licht für Arbeit oder Studium. Helles zweckmäßiges Licht. Klares Arbeitslicht für Produktivität. Büroartige Beleuchtung.",
        ),
    ),
    Scene(
        name="cozy",
        descriptions=(
            "Warm comfortable relaxing lighting. Soft ambient light for a cozy atmosphere. Calm intimate lighting for relaxing. Comfortable low brightness warm lighting.",
            "Warmes gemütliches entspannendes Licht. Sanftes Umgebungslicht für eine gemütliche Atmosphäre. Ruhige intime Beleuchtung zum Entspannen. Gemütliches warmes Licht mit niedriger Helligkeit.",
        ),
    ),
    Scene(
        name="calm",
        descriptions=(
            "Peaceful relaxing ambient lighting. Soft lighting for relaxation and calm. Gentle comfortable room illumination. A quiet soothing lighting atmosphere.",
            "Friedliche entspannende Umgebungsbeleuchtung. Sanftes Licht für Entspannung und Ruhe. Sanfte gemütliche Raumbeleuchtung. Eine ruhige beruhigende Lichtatmosphäre.",
        ),
    ),
    Scene(
        name="sleeping",
        descriptions=(
            "Very dim lighting for bedtime. Night lighting suitable for sleeping. Minimal soft illumination before sleep. Dark relaxing bedroom lighting.",
            "Sehr gedämpftes Licht für die Schlafenszeit. Nachtbeleuchtung geeignet zum Schlafen. Minimale sanfte Beleuchtung vor dem Schlafengehen. Dunkle entspannende Schlafzimmerbeleuchtung.",
        ),
    ),
]
