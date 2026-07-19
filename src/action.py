import abc
import json

from llama_cpp import Llama, LlamaRAMCache

from src import log
from src.handlers.lights import LightAction, actions_from_json

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
               Translate user requests to best matching lighting state.
               
               JSON represents light state in HSV and on/off:
               {"<id>":{"bri":0-254,"hue":0-65535,"sat":0-254,"on":bool}}
               light off -> {"<id>": {"on": false}}
               dim light -> {"<id>": {"bri": <low value>}}
               white light -> {"<id>": {"sat": 0, "bri": 254}}
               
               Interpretation examples:
               "sunset" -> warm orange, medium brightness
               "relaxing" -> warm dim light
               "movie night" -> dark, only TV lights
               "all lights" -> affects every available id
               
               Only state changed lights and changed field values.
               Output valid JSON only!
               """
}

USER_PROMPT = """
Current state: {current_state}
User request: {request}
"""


class ActionGenerator:
    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str):
        self._logger = log.new_logger(self.__class__.__name__)
        self._model = Llama(model_path=model_path,
                            cache=LlamaRAMCache(),
                            n_ctx=512, n_threads=4, n_gpu_layers=0, n_batch=512, verbose=False)
        self._warmup()

    def generate_lights(self, instruction: str, state: str | None = None) -> list[LightAction]:
        if not state:
            self._logger.warning(f"No current state given for instruction '{instruction}'")
            return []

        user_content = self._user_content(state, instruction)
        content = self._call_llm(user_content)
        self._logger.debug(f"LLM response: {content}")
        try:
            return actions_from_json(content)
        except json.JSONDecodeError as e:
            self._logger.warning(f"Failed to parse LLM response as JSON: raw={content}, error={e}")
            return []

    @staticmethod
    def _user_content(current_state: str, instruction: str) -> str:
        return USER_PROMPT.format(current_state=current_state, request=instruction)

    def _call_llm(self, user_content: str) -> str:
        messages = [
            SYSTEM_PROMPT,
            {
                "role": "user",
                "content": user_content
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
            messages=[SYSTEM_PROMPT],
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
    def get_state(self) -> str:
        """
        :return: The state of the objects this handler operates as JSON string.
        """
        pass


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action) -> int:
        return 0

    def get_state(self) -> str:
        return "{}"
