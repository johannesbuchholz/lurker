import abc
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

from src import log


class Action:
    """
    Intended to map speech-to-text translated snippets to some predefined command.
    """

    def __init__(self, keys: List[str], command: str | Dict):
        self.keys = keys
        self.command = command

    # TODO: Add regex matching
    def matches(self, snippet: str) -> Optional[str]:
        for k in self.keys:
            if k in snippet:
                return k
        return None


    def __str__(self):
        return "Action[keys: {}, command: {}]".format(self.keys, self.command)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keys": self.keys,
            "command": self.command
        }


class ActionRegistry:

    log = log.new_logger(__qualname__)

    @staticmethod
    def _load_action(action_path: str) -> Action:
        with open(action_path) as action_file_handle:
            action_dict: dict = json.load(action_file_handle)
            try:
                return Action(**action_dict)
            except Exception as e:
                ActionRegistry.log.warning("Could not load action from %s: " + str(e))

    def __init__(self, actions_path: str):
        self.actions_path = actions_path
        self.actions = {}

    # TODO: Enable periodic reloading or even reloading on usb device events
    def load_actions(self) -> None:
        actions = {}
        if not os.path.exists(self.actions_path):
            ActionRegistry.log.warning("No actions defined at " + self.actions_path)
            return
        for action_path in os.scandir(self.actions_path):
            abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
            loaded_action = ActionRegistry._load_action(str(abs_path))
            actions[action_path.name] = loaded_action
        ActionRegistry.log.info("Loaded actions: count=%s, files=%s", len(actions), list(actions.keys()))
        self.actions = actions

    def find(self, instruction: str) -> Optional[Action]:
        for action in self.actions.values():
            matching_key = action.matches(instruction.lower())
            if matching_key is not None:
                ActionRegistry.log.info("Found matching action for instruction: instruction=%s, key=%s", instruction, matching_key)
                return action
        return None


class ActionHandler(abc.ABC):
    """
    Baseclass to act on a specific instruction.
    This class is intended to be extended.
    """

    _logger = log.new_logger(__qualname__)
    implementation = None

    def __init__(self):
        self._logger = log.new_logger(self.__class__.__name__)

    def __init_subclass__(cls, **kwargs):
        if ActionHandler.implementation is None or cls.implementation is NOPHandler:
            ActionHandler.implementation = cls
            ActionHandler._logger.info(f"Registered action handler {cls}")
        else:
            raise RuntimeError(f"Only one subclass may be registered and {cls.implementation} has already been registered.")

    @abc.abstractmethod
    def handle(self, action: Action) -> bool:
        """
        :return: True iff the action has been handled successfully.
        """
        pass


class NOPHandler(ActionHandler):

    def __init__(self):
        super().__init__()

    def handle(self, action: Action) -> bool:
        return True