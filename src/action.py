import abc
import json
from typing import cast

from llama_cpp import Llama, LlamaRAMCache, CreateCompletionResponse

from src import log
from src.handlers.lights import LightAction, actions_from_json

PROMPT_TEMPLATE = """<system>
Translate user requests to best matching lighting state.
Output valid JSON only!
Json represents light state in HSV: 
{"<id>":{"bri":0-254,"hue":0-65535,"sat":0-254,"on":true|false}}
Syntax-Example:
{"0": {"bri":90,"hue":420},"1":{"on":false},"2,3":{"bri":254}}
Interpretation Examples:
"sunset" -> warm orange, medium brightness
"relaxing" -> warm dim light
"movie night" -> dark, only tv lights
<user>
{user_content}
<assistant>"""

USER_PROMPT = """
Current state: {current_state}
User instruction: {instruction}
"""


class ActionGenerator:

    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str):
        self._logger = log.new_logger(self.__class__.__name__)
        self._model = Llama(model_path=model_path,
                            cache=LlamaRAMCache(),
                            n_ctx=128, n_threads=4, n_gpu_layers=0, n_batch=128, verbose=False)
        self._warmup()

    def generate_lights(self, instruction: str, current_state: str = "{}") -> list[LightAction]:
        user_content = self._user_content(current_state, instruction)
        content = self._call_llm(user_content)
        self._logger.debug(f"LLM response: {content}")
        try:
            return actions_from_json(content)
        except json.JSONDecodeError as e:
            self._logger.warning(f"Failed to parse LLM response as JSON: raw={content}, error={e}")
            return []

    @staticmethod
    def _user_content(current_state: str, instruction: str) -> str:
        return USER_PROMPT.format(current_state=current_state, instruction=instruction)

    def _call_llm(self, user_content: str) -> str:
        prompt = PROMPT_TEMPLATE.format(user_content=user_content)
        response: CreateCompletionResponse = cast(CreateCompletionResponse,
                                                  self._model.create_completion(
                                                      prompt=prompt,
                                                      temperature=0.,
                                                      max_tokens=128,
                                                      stream=False
                                                  ))
        return response["choices"][0]["text"]

    def _warmup(self) -> None:
        self._model.create_completion(
            prompt=PROMPT_TEMPLATE,
            temperature=0.,
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


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action) -> int:
        return 0
