import abc
import os
import re
from typing import Any, Collection

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from src.actions.embedding import Embedder, best_match
from src.actions.intents import apply_intent
from src.actions.models import Describable, light_descriptions
from src.handlers.lights import Light, LightAction

LIGHT_MATCH_THRESHOLD = 0.55
LLM_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def resolve_llm_model_path(lurker_home: str) -> str:
    """Resolve the default embedding model path inside a lurker home directory."""
    return os.path.join(lurker_home, "models", "onnx", LLM_MODEL_NAME)

ALL_LIGHTS_PATTERN = re.compile(
    r"\balle(?:n)?\s+lichter\b|\balle(?:s|n)?\s*(?:ein|aus|an)\b"
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

class LoadedHandlerType:
    cls: type | None = None

    @staticmethod
    def get_implementation() -> type:
        return NOPHandler if LoadedHandlerType.cls is None else LoadedHandlerType.cls


class ActionHandler(abc.ABC):
    """
    Baseclass to act on a specific instruction.
    This class is intended to be extended.
    """

    _logger = log.new_logger(__qualname__)

    def __init__(self, **kwargs):
        self._logger = log.new_logger(self.__class__.__name__)

    def __init_subclass__(cls, **kwargs):
        if cls.__module__ == ActionHandler.__module__:
            # ignore implementations from this module
            return
        if LoadedHandlerType.cls is None:
            LoadedHandlerType.cls = cls
            ActionHandler._logger.debug(f"Registered action handler {cls}")
        else:
            raise RuntimeError(
                f"Only one subclass may be registered and {LoadedHandlerType.cls} has already been registered.")

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
