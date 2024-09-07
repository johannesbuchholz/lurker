import json
import os
from pathlib import Path
from typing import List, Tuple

from src import log
from src.client import HueClient, LightPutRequest, LightSelector

LOGGER = log.new_logger(__name__)


class Action:
    """
    Intended to map speech-to-text translated snippets to some predefined instructions.
    """

    def __init__(self, key_paragraphs: List[str], light_action: Tuple[LightSelector, LightPutRequest]):
        self.key_paragraphs = key_paragraphs
        self.light_action = light_action

    def is_matching(self, snippet: str) -> bool:
        for p in self.key_paragraphs:
            if p in snippet:
                return True
        return False

    def __str__(self):
        return ("Action[keys: {}, light_action: ({}, {})]"
                .format(self.key_paragraphs, self.light_action[0], self.light_action[1]))


class HueActionRegistry:

    def __init__(self, client: HueClient, actions_path: str):
        self.client = client
        self.actions_path = actions_path
        self.actions = {}

    def load_actions(self) -> None:
        actions = {}
        if not os.path.exists(self.actions_path):
            LOGGER.warning("No actions defined at " + self.actions_path)
            return
        for action_path in os.scandir(self.actions_path):
            abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
            loaded_action = _load_action(str(abs_path))
            actions[action_path.name] = loaded_action
        LOGGER.info("Loaded actions: count=%s, files=%s", len(actions), list(actions.keys()))
        self.actions = actions

    def act(self, instruction: str) -> bool:
        # matching_action = next((action for action in self.actions.values() if action.is_matching(instruction)), None)
        for action in self.actions.values():
            if action.is_matching(instruction.lower()):
                LOGGER.info("Found action %s for instruction '%s'", action, instruction)
                self.client.light(action.light_action)
                return True
        LOGGER.info("Could not find action for instruction '%s'", instruction)
        return False


def _load_action(action_path: str) -> Action:
    with open(action_path) as action_file_handle:
        action_dict: dict = json.load(action_file_handle)
        try:
            return Action(
                key_paragraphs=action_dict["keys"],
                light_action=(LightSelector(action_dict["lights"]), LightPutRequest(**action_dict["request"])))
        except Exception as e:
            LOGGER.warning("Could not load action from %s: " + str(e))
