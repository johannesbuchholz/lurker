import abc
from typing import Any

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from src.actions import models, embedding
from src.actions.embedding import Embedder
from src.actions.models import Intent
from src.handlers.lights import LightAction, LightState


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
        intent = self._get_intent(instruction)
        if intent is None:
            self._logger.info(f"Intent of '{instruction}' not found")
            return []
        names = ",".join(self._extract_light_names(state))
        # TODO: Implement workflow according to plan.md
        self._logger.debug(f"Intent of '{instruction}': {intent}")
        self._logger.warning("NOT YET IMPLEMENTED")
        return []

    def _get_intent(self, instruction: str) -> Intent | None:
        match = embedding.best_match(models.INTENTS, self._embedder, instruction, threshold=0.5)
        return match if isinstance(match, Intent) else None

    @staticmethod
    def _extract_light_names(state: dict[str, Any]) -> list[str]:
        return [v.name for _, v in state.items() if isinstance(v, LightState)]

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
