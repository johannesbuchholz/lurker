import abc
import re
from typing import Any, Collection

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from src.actions.embedding import Embedder, best_match
from src.actions.intents import apply_intent
from src.actions.models import Describable, light_descriptions
from src.handlers.lights import Light, LightAction, State

LIGHT_MATCH_THRESHOLD = 0.55

ALL_LIGHTS_PATTERN = re.compile(
    r"\ballen?\s+lichter\b|\balle[sn]?\s*(?:ein|aus|an)\b"
    r"|\ball\s+lights?\b|\ball(?:s|es)?\b|\beverything\b",
    re.IGNORECASE,
)
NAME_STOP_WORDS = {"light", "lights", "lamp", "lamps", "licht", "lichter", "lampe", "lampen", "room", "zimmer"}


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

    @staticmethod
    def _name_tokens(name: str) -> list[str]:
        """Split a light name into significant lowercase tokens (used to detect keyword matches in instructions)."""
        return [
            word
            for word in re.split(r"\W+", name.lower())
            if word and (len(word) >= 2 or word.isdigit()) and word not in NAME_STOP_WORDS
        ]

    @staticmethod
    def _match_by_name_tokens(instruction: str, names: Collection[str]) -> list[str]:
        """Deterministically find lights whose name tokens occur in the instruction (use before embedding-based matching)."""
        normalized = instruction.lower()
        return [
            name
            for name in names
            if any(token in normalized for token in ActionGenerator._name_tokens(name))
        ]

    def generate_lights(self, instruction: str, state: dict[str, Any]) -> list[LightAction]:
        lights = [v for v in state.values() if isinstance(v, Light)]
        names = self.guess_lights(instruction, [light.name for light in lights])
        affected = [light for light in lights if light.name in names]
        if not affected:
            affected = lights
        new_lights = apply_intent(instruction, affected, self._embedder)
        if new_lights is None:
            self._logger.info(f"No intent matched for instruction: '{instruction}'")
            return []
        return [LightAction([light.id], light.state) for light in new_lights]

    def guess_lights(self, instruction: str, available_lights: Collection[str]) -> Collection[str]:
        normalized = instruction.lower()
        if ALL_LIGHTS_PATTERN.search(normalized):
            return list(available_lights)

        matched = ActionGenerator._match_by_name_tokens(normalized, available_lights)
        if matched:
            return matched

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


_DUMMY_LIGHTS: dict[str, Light] = {
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


class DummyHandler(ActionHandler):
    """Returns a fixed example light state and logs actions without executing them."""

    def handle(self, action) -> int:
        self._logger.info(f"Logging action without executing it: {action}")
        return 0

    def get_state(self) -> dict[str, Any]:
        return dict(_DUMMY_LIGHTS)
