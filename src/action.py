import abc
import json
import os
import re
from pathlib import Path
from threading import Thread
from time import sleep
from typing import List, Dict, Optional, Any, Pattern, Match, Union, Tuple

from src import log


class Action:
    """
    A mapping of key paragraphs to a command.
    """

    @staticmethod
    def compile_regexes(keys: List[str]) -> List[Pattern]:
        patterns = []
        for key in keys:
            if key.startswith("/") and key.endswith("/"):
                pattern_string = key[1:-1]
            else:
                pattern_string = ".*" + key + ".*"
            patterns.append(re.compile(pattern_string))
        return patterns

    def __init__(self, keys: List[str], command: Union[str, int, None, Dict[str, Any]]):
        self.keys = keys
        self.command = command
        self.patterns: List[Pattern] = self.compile_regexes(self.keys)

    def matches(self, snippet: str) -> Optional[Match]:
        for p in self.patterns:
            match = p.match(snippet)
            if match is not None:
                return match
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keys": self.keys,
            "command": self.command
        }

    def __str__(self):
        return f"Action[keys: {self.keys}, command: {self.command}]"


class ActionRegistry:

    _logger = log.new_logger(__qualname__)

    @staticmethod
    def _load_action(action_path: Union[str, Path]) -> Action:
        with open(action_path) as action_file_handle:
            action_dict: dict = json.load(action_file_handle)
            try:
                return Action(**action_dict)
            except Exception as e:
                ActionRegistry._logger.warning(f"Could not load action from %s: {e}")

    def __init__(self, actions_path: str):
        self.actions_path = actions_path
        self.actions: Dict[str, Tuple[int, Action]] = {}    # filename -> (modified time, action)

    def find(self, instruction: str) -> Optional[Tuple[Action, Match[str]]]:
        for _, action in self.actions.values():
            match = action.matches(instruction.lower())
            if match is not None:
                self._logger.info(f"Found matching action for instruction: instruction={instruction}, match={match}")
                return action, match
        return None

    def start_periodic_reloading_in_background(self, interval_duration_s) -> None:
        self._logger.info(f"Starting periodic reloading of new or updated actions: location={self.actions_path}, interval_duration_s={interval_duration_s}")
        def reloader() -> None:
            while True:
                sleep(interval_duration_s)
                self._reload_actions()
        Thread(target=reloader, name="lurker_action_reloader", daemon=True).start()

    def load_actions_once(self) -> None:
        if not os.path.exists(self.actions_path):
            self._logger.warning(f"No actions defined at {self.actions_path}")
            return
        for action_path in os.scandir(self.actions_path):
            if not action_path.is_file():
                continue
            abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
            loaded_action = ActionRegistry._load_action(abs_path)
            self.actions[action_path.name] = (int(abs_path.stat().st_mtime), loaded_action)
        self._logger.info(f"Loaded actions: count={len(self.actions)}, files={list(self.actions.keys())}")

    def _reload_actions(self) -> None:
        try:
            self._logger.debug(f"About to reload changed or new actions from {self.actions_path}")
            for action_path in os.scandir(self.actions_path):
                if not action_path.is_file():
                    continue
                abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
                mtime: int = int(abs_path.stat().st_mtime)
                if abs_path.name not in self.actions or self.actions[abs_path.name][0] < mtime:
                    # file is unknown or touched: reload
                    self.actions[abs_path.name] = (mtime, ActionRegistry._load_action(abs_path))
                    self._logger.info(f"Reloaded action {abs_path.name}")
        except Exception as e:
            self._logger.warning(f"Could not reload action: {e}", exc_info=e)


class LoadedHandlerType:
    cls: Optional[type] = None

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
    def handle(self, action: Action, key_match: Match[str]) -> int:
        """
        :param action: The action object to handle.
        :param key_match: The match object resulting from successfully matching one of the keys associated with the supplied action.
        :return: An exit code of zero iff the action has been handled successfully.
        """
        pass


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action: Action, key_match: Match[str]) -> int:
        return 0
