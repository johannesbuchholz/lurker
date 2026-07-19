import abc
import json
from pathlib import Path

from src import log
from src.utils import Action


class ActionRegistry:

    _logger = log.new_logger(__qualname__)

    @staticmethod
    def _load_action(action_path: str | Path) -> Action | None:
        with open(action_path) as action_file_handle:
            action_dict: dict = json.load(action_file_handle)
            try:
                return Action(**action_dict)
            except Exception as e:
                ActionRegistry._logger.warning(f"Could not load action from %s: {e}")
                return None

    def __init__(self, actions_path: str):
        self.actions_path = actions_path
        self.actions: dict[str, tuple[int, Action]] = {}    # filename -> (modified time, action)

    def find(self, instruction: str) -> Action | None:
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
    def handle(self, action: Action) -> int:
        """
        :param action: The action object to handle.
        :return: An exit code of zero iff the action has been handled successfully.
        """
        pass


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action: Action) -> int:
        return 0
