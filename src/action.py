import abc

from llama_cpp import Llama

from src import log
from src.handlers.lights import LightAction

PROMPT_TEMPLATE = """
Translate the user instruction to the best matching lighting state. Output valid JSON only!
Json structure represents light state in HSV: 
{"<light id>": {"bri": <brightness int 0-254>, "heu": <int 0-65535>, "sat": <int 0-254>, "on" <bool>}
Example (Comma IDs target multiple lights):
{"0": {"bri":90,"hue":420},"1":{"on":false},"2,3":{"bri":254}}
Current state:
{current_state}
User instruction:
{instruction}
"""

class ActionGenerator:

    _logger = log.new_logger(__qualname__)

    def __init__(self, model_path: str):
        self._logger = log.new_logger(self.__class__.__name__)
        self._model = Llama(model_path=model_path, n_ctx=512, n_threads=4, n_gpu_layers=0, n_batch=256, verbose=False)

    def generate_lights(self, instruction: str) -> list[LightAction]:
        # TODO: Implement using granite 350 llm
        pass



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
            raise RuntimeError(f"Only one subclass may be registered and {LoadedHandlerType.cls} has already been registered.")

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
