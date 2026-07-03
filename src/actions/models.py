from __future__ import annotations

import re
from dataclasses import dataclass

from src.handlers.lights import State


@dataclass(frozen=True, slots=True)
class Describable:
    name: str
    descriptions: tuple[str, ...]

    def __str__(self):
        return self.name


@dataclass(frozen=True, slots=True)
class Scene(Describable):
    state: State
    pattern: re.Pattern | None = None


def light_descriptions(name: str) -> tuple[str, ...]:
    """Build the embedding descriptions for a light (use for embedding-based light matching when keyword matching fails)."""
    normalized = name.lower().strip()
    return tuple(dict.fromkeys([normalized, f"{normalized} light"]))


SCENES: list[Scene] = [
    Scene(
        name="movie_night",
        descriptions=(
            "Dark cinematic lighting for watching movies. A cinema atmosphere with comfortable low lighting. Relaxing evening lighting for watching a film. Dim ambient lights suitable for television or movies.",
        ),
        state=State(on=True, hue=30, sat=50, bri=15),
        pattern=re.compile(r"\b(movie|movies|film|kino|cinema|fernsehen)\b", re.IGNORECASE),
    ),
    Scene(
        name="sunset",
        descriptions=(
            "Warm orange evening lighting. Soft golden light similar to sunset. Relaxing warm colors for an evening atmosphere. Orange and warm ambient lighting.",
        ),
        state=State(on=True, hue=25, sat=90, bri=70),
        pattern=re.compile(r"\b(sunset|sun set|sonnenuntergang|abendrot)\b", re.IGNORECASE),
    ),
    Scene(
        name="morning_mood",
        descriptions=(
            "Bright refreshing light for the morning. Wake up lighting that feels natural and energizing. Clear bright lighting for starting the day. Fresh daylight-like room illumination.",
        ),
        state=State(on=True, hue=50, sat=30, bri=100),
        pattern=re.compile(r"\b(morning|morgen|aufwachen|aufstehen|wachwerden)\b", re.IGNORECASE),
    ),
    Scene(
        name="work",
        descriptions=(
            "Focused lighting for working or studying. Bright practical lighting. Clear task lighting for productivity. Office-style illumination.",
        ),
        state=State(on=True, hue=200, sat=20, bri=100),
        pattern=re.compile(r"\b(work|working|arbeiten|arbeit|stud(y|ying)|studium|lernen|konzentration)\b", re.IGNORECASE),
    ),
    Scene(
        name="cozy",
        descriptions=(
            "Warm comfortable relaxing lighting. Soft ambient light for a cozy atmosphere. Calm intimate lighting for relaxing. Comfortable low brightness warm lighting.",
        ),
        state=State(on=True, hue=30, sat=60, bri=40),
        pattern=re.compile(r"\b(cozy|coziness|gemütlich|gemuetlich|kuschelig|snug)\b", re.IGNORECASE),
    ),
    Scene(
        name="calm",
        descriptions=(
            "Peaceful relaxing ambient lighting. Soft lighting for relaxation and calm. Gentle comfortable room illumination. A quiet soothing lighting atmosphere.",
        ),
        state=State(on=True, hue=180, sat=30, bri=30),
        pattern=re.compile(r"\b(calm|peaceful|ruhig|friedlich|entspannt|relax)\b", re.IGNORECASE),
    ),
    Scene(
        name="sleeping",
        descriptions=(
            "Very dim lighting for bedtime. Night lighting suitable for sleeping. Minimal soft illumination before sleep. Dark relaxing bedroom lighting.",
        ),
        state=State(on=True, hue=20, sat=40, bri=5),
        pattern=re.compile(r"\b(sleep|sleeping|schlaf|schlafen|bedtime|bettgeh)\b", re.IGNORECASE),
    ),
]
