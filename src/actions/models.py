from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Protocol

import numpy as np
from numpy.typing import NDArray

from src.handlers.lights import LightState


class Describable(Protocol):
    descriptions: tuple[str, ...]


T = TypeVar("T", bound=Describable)


@dataclass(frozen=True, slots=True)
class Embedded(Generic[T]):
    item: T
    embeddings: tuple[NDArray[np.float32], ...]


@dataclass(frozen=True, slots=True)
class Intent:
    """
    Candidates:
    POWER
    COLOR
    BRIGHTNESS
    SCENE
    """
    name: str
    descriptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Scene:
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
    name: str
    descriptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Light:
    id: str
    name: str
    descriptions: tuple[str, ...]
    state: LightState


def embed(embedder: Callable[[str], NDArray[np.float32]], items: list[T]) -> list[Embedded[T]]:
    return [
        Embedded(item=item, embeddings=tuple(embedder(description) for description in item.descriptions), )
        for item in items
    ]


def get_lights(list_states: list[LightState]) -> list[Light]:
    result = []
    for state in list_states:
        light_name = state.name
        light = Light(name=light_name, descriptions=_generate_light_descriptions(light_name), state=state)
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


INTENTS: list[Intent] = [
    Intent(
        name="power",
        descriptions=(
            "Turn lights on or off",
            "Change the power state of one or more lights",
            "Switch a lamp or group of lights between on and off",
            "Enable or disable lighting",
            "Control whether lights are illuminated or turned off",
        ),
    ),
    Intent(
        name="brightness",
        descriptions=(
            "Adjust the brightness level of lights",
            "Make lights brighter or dimmer",
            "Change the intensity of lighting",
            "Set or modify the light brightness",
            "Increase or decrease how much light a lamp produces",
        ),
    ),
    Intent(
        name="color",
        descriptions=(
            "Change the color of lights",
            "Set lights to a specific color",
            "Adjust the hue or saturation of lighting",
            "Create colored lighting effects",
            "Change the appearance of lights using different colors",
        ),
    ),
    Intent(
        name="scene",
        descriptions=(
            "Activate a lighting scene or atmosphere",
            "Set a coordinated lighting mood for an activity or situation",
            "Apply a predefined lighting arrangement",
            "Create an overall room atmosphere using multiple lights",
            "Change several lights together to create a specific mood",
        ),
    ),
]

SCENES: list[Scene] = [
    Scene(
        name="movie_night",
        descriptions=(
            "Dark cinematic lighting for watching movies",
            "A cinema atmosphere with comfortable low lighting",
            "Relaxing evening lighting for watching a film",
            "Dim ambient lights suitable for television or movies",
        ),
    ),
    Scene(
        name="sunset",
        descriptions=(
            "Warm orange evening lighting",
            "Soft golden light similar to sunset",
            "Relaxing warm colors for an evening atmosphere",
            "Orange and warm ambient lighting",
        ),
    ),
    Scene(
        name="morning_mood",
        descriptions=(
            "Bright refreshing light for the morning",
            "Wake up lighting that feels natural and energizing",
            "Clear bright lighting for starting the day",
            "Fresh daylight-like room illumination",
        ),
    ),
    Scene(
        name="work",
        descriptions=(
            "Focused lighting for working or studying",
            "Bright practical lighting",
            "Clear task lighting for productivity",
            "Office-style illumination",
        ),
    ),
    Scene(
        name="cozy",
        descriptions=(
            "Warm comfortable relaxing lighting",
            "Soft ambient light for a cozy atmosphere",
            "Calm intimate lighting for relaxing",
            "Comfortable low brightness warm lighting",
        ),
    ),
    Scene(
        name="calm",
        descriptions=(
            "Peaceful relaxing ambient lighting",
            "Soft lighting for relaxation and calm",
            "Gentle comfortable room illumination",
            "A quiet soothing lighting atmosphere",
        ),
    ),
    Scene(
        name="sleeping",
        descriptions=(
            "Very dim lighting for bedtime",
            "Night lighting suitable for sleeping",
            "Minimal soft illumination before sleep",
            "Dark relaxing bedroom lighting",
        ),
    ),
]
