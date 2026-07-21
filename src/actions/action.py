import abc
from typing import Any

import onnxruntime as ort
from tokenizers.tokenizers import Tokenizer

from src import log
from src.actions import models, embedding
from src.actions.embedding import Embedder, Embedded
from src.actions.models import Light, Scene, Intent
from src.handlers.lights import LightAction, LightState


class ActionGenerator:
    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str, state: dict[str, Any]):
        self._logger = log.new_logger(self.__class__.__name__)
        if len(state) < 1:
            self._logger.warning("No state given ActionGenerator!")
        light_state: list[LightState] = [v for _, v in state.items() if isinstance(v, LightState)]
        self.embedder: Embedder = Embedder(
            tokenizer=Tokenizer.from_file(f"{model_path}/tokenizer.json"),
            session=ort.InferenceSession(f"{model_path}/model_O4.onnx", providers=["CPUExecutionProvider"])
        )
        self.lights, self.scenes, self.intents = self._init_embeddings(light_state)

    def generate_lights(self, instruction: str) -> list[LightAction]:
        # TODO: Implement workflow according to plan.md
        self._logger.warning("NOT YET IMPLEMENTED")
        return []

    def _get_intent(self, instruction: str) -> Intent | None:
        return embedding.best_match(self.intents, instruction)

    def _init_embeddings(self, light_state: list[LightState]) \
            -> tuple[list[Embedded[Light]], list[Embedded[Scene]], list[Embedded[Intent]]]:
        lights = models.as_lights(light_state)
        return (
            embedding.embed_items(self.embedder, lights),
            embedding.embed_items(self.embedder, models.SCENES),
            embedding.embed_items(self.embedder, models.INTENTS)
        )


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
