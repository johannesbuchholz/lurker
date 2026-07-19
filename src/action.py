import abc
from typing import Any

from llama_cpp import Llama, LlamaRAMCache

from src import log
from src.handlers.lights import LightAction, actions_from_json, LightState

SYSTEM_PROMPT = """
Extract affected lights and action from a user request.
Schema:
{"lights": [<affected light names>], "action": <the user requested modification>}
Output valid JSON only!
Only state lights that are requested to change. Always fill "lights" and "action".
Available modification types (action): ON, OFF, BRIGHTER, WARMER, CHANGE_COLOR, OTHER
Available light names:
"""


class ActionGenerator:
    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str, state: dict[str, Any]):
        self._logger = log.new_logger(self.__class__.__name__)
        self._model = Llama(model_path=model_path,
                            cache=LlamaRAMCache(),
                            n_ctx=256, n_threads=4, n_gpu_layers=0, n_batch=256, verbose=False)
        if len(state) < 1:
            self._logger.warning("No state given ActionGenerator!")
        self.light_names: list[str] = [v.name for _, v in state.items() if isinstance(v, LightState) and v.name is not None]
        self._warmup()

    def generate_lights(self, instruction: str, state: str | None = None) -> list[LightAction]:
        if not state:
            self._logger.warning(f"No current state given for instruction '{instruction}'")
            return []

        content = self._call_llm(instruction)
        self._logger.debug(f"LLM response: {content}")
        try:
            return actions_from_json(content)
        except Exception as e:
            self._logger.warning(f"Failed to parse LLM response as JSON: raw={content}, error={e}")
            return []

    def _system_message(self) -> dict[str, str]:
        return {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n" + ", ".join(self.light_names)
        }

    def _call_llm(self, instruction: str) -> str:
        messages = [
            self._system_message(),
            {
                "role": "user",
                "content": instruction
            },
        ]
        self._logger.debug(f"Prompting: {messages}")
        response = self._model.create_chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        )
        return response["choices"][0]["message"]["content"]

    def _warmup(self) -> None:
        self._model.create_chat_completion(
            messages=[self._system_message()],
            temperature=0.1,
            max_tokens=1
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
