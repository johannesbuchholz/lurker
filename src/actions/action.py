import abc
import re
from typing import Any, Collection

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from src.actions import intents
from src.actions.embedding import Embedder, best_match
from src.actions.models import Describable, light_descriptions
from src.handlers.lights import Light, LightAction, State

LIGHT_MATCH_THRESHOLD = 0.55

ALL_LIGHTS_PATTERN = re.compile(
    r"\ballen?\s+lichter?\b"
    r"|\balle[sn]?\s+(?:licht(?:er)?|lampe|lampen)?\s*(?:ein|aus|an)\b"
    r"|\ball\s+lights?\b|\ball(?:s|es)?\b|\beverything\b",
    re.IGNORECASE,
)
NAME_STOP_WORDS = {
    "light", "lights", "lamp", "lamps", "licht", "lichter", "lampe", "lampen", "room", "zimmer",
    "on", "in", "the", "a", "an", "of", "at", "to", "for", "with", "by",
    "ein", "eine", "einem", "einen", "der", "die", "das", "den", "dem", "des",
    "an", "auf", "in", "mit", "von", "zu", "bei", "nach", "über", "unter",
}


def _name_tokens(name: str) -> list[str]:
    """Split a light name into significant lowercase tokens."""
    return [
        word
        for word in re.split(r"\W+", name.lower())
        if word and (len(word) >= 2 or word.isdigit()) and word not in NAME_STOP_WORDS
    ]


def _try_room_filtering(instruction: str, available_lights: Collection[str]) -> Collection[str]:
    instruction_words = set(instruction.split())
    scores: list[tuple[int, str]] = []
    for name in available_lights:
        tokens = _name_tokens(name)
        hits = sum(1 for t in tokens if t in instruction_words)
        if hits > 0:
            scores.append((hits, name))
    if not scores:
        return []
    max_hits = max(h for h, _ in scores)
    return [name for h, name in scores if h == max_hits]


class ActionGenerator:
    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str, initial_state: dict[str, Any]):
        self._logger = log.new_logger(self.__class__.__name__)
        if len(initial_state) < 1:
            self._logger.warning("No state given ActionGenerator!")
        self._embedder: Embedder = Embedder(
            tokenizer=Tokenizer.from_file(f"{model_path}/tokenizer.json"),
            session=ort.InferenceSession(f"{model_path}/model_O4.onnx", providers=["CPUExecutionProvider"])
        )

    def generate_lights(self, instruction: str, state: dict[str, Any]) -> list[LightAction]:
        lights = [v for v in state.values() if isinstance(v, Light)]
        names = self.guess_lights(instruction, [light.name for light in lights])
        affected = [light for light in lights if light.name in names]
        if not affected:
            affected = lights
        new_lights = intents.guess_intent_and_apply(instruction, affected, self._embedder)
        if new_lights is None:
            self._logger.info(f"No intent matched for instruction: '{instruction}'")
            return []
        return [LightAction([light.id], light.state) for light in new_lights]

    def guess_lights(self, instruction: str, available_lights: Collection[str]) -> Collection[str]:
        """
        NOTE: _extract_room relies on light name tokens appearing literally in the instruction text.
        This only works when light names and the instruction share the same language;
        cross-language room qualifiers (e.g. German "küche" vs English light name "Kitchen") will not be detected.
        """
        normalized = instruction.lower()
        room_lights = _try_room_filtering(normalized, available_lights)
        if room_lights:
            return room_lights
        if ALL_LIGHTS_PATTERN.search(normalized):
            return list(available_lights)
        # no room specified and no "all"-quantifier detected: Apply embeddings as fallback
        items = [Describable(name=name, descriptions=light_descriptions(name)) for name in available_lights]
        matches = best_match(items, self._embedder, instruction, top_n=-1, threshold=LIGHT_MATCH_THRESHOLD)
        return [item.name for item in matches]

class ActionHandler(abc.ABC):
    """
    Baseclass to act on a specific instruction.
    This class is intended to be extended.
    """

    _logger = log.new_logger(__qualname__)

    def __init__(self, **kwargs):
        self._logger = log.new_logger(self.__class__.__name__)

    @abc.abstractmethod
    def handle(self, action) -> int:
        """
        :param action: The action object to handle.
        :return: An exit code of zero iff the action has been handled successfully.
        """
        pass

    @abc.abstractmethod
    def get_state(self) -> dict[str, Any]:
        """
        :return: The state of the objects this handler operates as JSON string.
        """
        pass


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action) -> int:
        return 0

    def get_state(self) -> dict[str, Any]:
        return {}


_DUMMY_LIGHTS_EN: dict[str, Light] = {
    "1": Light(id="1", name="Living Room Lamp", state=State(on=True, bri=50, hue=44, sat=79)),
    "2": Light(id="2", name="Desk Lamp", state=State(on=True, bri=100, hue=220, sat=39)),
    "3": Light(id="3", name="Bedroom Light", state=State(on=False, bri=0, hue=0, sat=0)),
    "4": Light(id="4", name="Living Room Entry", state=State(on=True, bri=50, hue=44, sat=79)),
    "5": Light(id="5", name="Living Room Couch", state=State(on=True, bri=79, hue=192, sat=59)),
    "6": Light(id="6", name="Living Room Ceiling", state=State(on=True, bri=100, hue=220, sat=39)),
    "7": Light(id="7", name="Living Room Table", state=State(on=True, bri=35, hue=55, sat=71)),
    "8": Light(id="8", name="Living Room Desk", state=State(on=False, bri=0, hue=0, sat=0)),
    "9": Light(id="9", name="Kitchen", state=State(on=True, bri=59, hue=27, sat=87)),
    "10": Light(id="10", name="Floor 1", state=State(on=True, bri=39, hue=165, sat=51)),
    "11": Light(id="11", name="Floor 2", state=State(on=True, bri=30, hue=110, sat=63)),
    "12": Light(id="12", name="Bedroom Ceiling", state=State(on=False, bri=0, hue=0, sat=0)),
    "13": Light(id="13", name="Bedroom Nightstand Alex", state=State(on=True, bri=71, hue=66, sat=35)),
    "14": Light(id="14", name="Bedroom Nightstand Jenny", state=State(on=True, bri=87, hue=247, sat=47)),
}

_DUMMY_LIGHTS_DE: dict[str, Light] = {
    "1": Light(id="1", name="Wohnzimmer Lampe", state=State(on=True, bri=50, hue=44, sat=79)),
    "2": Light(id="2", name="Schreibtisch Lampe", state=State(on=True, bri=100, hue=220, sat=39)),
    "3": Light(id="3", name="Schlafzimmer Licht", state=State(on=False, bri=0, hue=0, sat=0)),
    "4": Light(id="4", name="Wohnzimmer Eingang", state=State(on=True, bri=50, hue=44, sat=79)),
    "5": Light(id="5", name="Wohnzimmer Couch", state=State(on=True, bri=79, hue=192, sat=59)),
    "6": Light(id="6", name="Wohnzimmer Decke", state=State(on=True, bri=100, hue=220, sat=39)),
    "7": Light(id="7", name="Wohnzimmer Tisch", state=State(on=True, bri=35, hue=55, sat=71)),
    "8": Light(id="8", name="Wohnzimmer Schreibtisch", state=State(on=False, bri=0, hue=0, sat=0)),
    "9": Light(id="9", name="Küche", state=State(on=True, bri=59, hue=27, sat=87)),
    "10": Light(id="10", name="Etage 1", state=State(on=True, bri=39, hue=165, sat=51)),
    "11": Light(id="11", name="Etage 2", state=State(on=True, bri=30, hue=110, sat=63)),
    "12": Light(id="12", name="Schlafzimmer Decke", state=State(on=False, bri=0, hue=0, sat=0)),
    "13": Light(id="13", name="Schlafzimmer Nachttisch Alex", state=State(on=True, bri=71, hue=66, sat=35)),
    "14": Light(id="14", name="Schlafzimmer Nachttisch Jenny", state=State(on=True, bri=87, hue=247, sat=47)),
}

_DUMMY_LIGHTS: dict[str, Light] = _DUMMY_LIGHTS_EN


class DummyHandler(ActionHandler):
    """Returns a fixed example light state and logs actions without executing it."""

    def __init__(self, language: str = "en"):
        super().__init__()
        self._language = language

    def handle(self, action) -> int:
        self._logger.info(f"Logging action without executing it: {action}")
        return 0

    def get_state(self) -> dict[str, Any]:
        if self._language == "de":
            return dict(_DUMMY_LIGHTS_DE)
        return dict(_DUMMY_LIGHTS_EN)
