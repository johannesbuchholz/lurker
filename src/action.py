import abc
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable

from src import log

LOGGER = log.new_logger(__name__)

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

    def __repr__(self):
        return "Action[keys: {}, command: {}]".format(self.keys, self.command)

class ActionRegistry:

    @staticmethod
    def _load_action(action_path: str) -> Action:
        with open(action_path) as action_file_handle:
            action_dict: dict = json.load(action_file_handle)
            try:
                return Action(**action_dict)
            except Exception as e:
                LOGGER.warning("Could not load action from %s: " + str(e))

    def __init__(self, actions_path: str):
        self.actions_path = actions_path
        self.actions = {}

    # TODO: Enable periodic reloading or even reloading on usb device events
    def load_actions(self) -> None:
        actions = {}
        if not os.path.exists(self.actions_path):
            LOGGER.warning("No actions defined at " + self.actions_path)
            return
        for action_path in os.scandir(self.actions_path):
            abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
            loaded_action = ActionRegistry._load_action(str(abs_path))
            actions[action_path.name] = loaded_action
        LOGGER.info("Loaded actions: count=%s, files=%s", len(actions), list(actions.keys()))
        self.actions = actions

    def find(self, instruction: str) -> Optional[Action]:
        for action in self.actions.values():
            matching_key = action.matches(instruction.lower())
            if matching_key is not None:
                LOGGER.info("Found matching action for instruction: instruction=%s, key=%s", instruction, matching_key)
                return action
        return None

class ActionHandler(abc.ABC):
    """
    Baseclass to handle act on a specific instruction.
    This class is intended to be extended.
    """

    SPECIAL_COMMANDS: Dict[str, Callable[[], None]] = {"EXIT": exit}

    def handle(self, action: Action) -> bool:
        command = action.command
        if type(command) is str:
            callable_command = ActionHandler.SPECIAL_COMMANDS.get(command, None)
            if callable_command is not None:
                self._logger.info(f"Handling special command: {command}")
                callable_command()
                return True

        return self._handle_internal(action)


    @abc.abstractmethod
    def _handle_internal(self, action: Action) -> bool:
        """
        Implement by extending classes.
        :return: True iff the action has been handled successfully.
        """
        pass
