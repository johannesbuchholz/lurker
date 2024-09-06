import json
import os
from pathlib import Path
from typing import List, Iterable, Tuple, Dict

from src import log
from src import text
from src.client import HueClient, LightPutRequest, LightSelector

LOGGER = log.new_logger(__name__)


def _are_items_contained_in_order(items: List, container: Iterable) -> bool:
    items_i = 0
    for candidate in container:
        if items_i >= len(items):
            return True
        if candidate == items[items_i]:
            items_i += 1
    return items_i >= len(items)


class Action:
    """
    Intended to map speech-to-text translated snippets to some predefined instructions.
    """

    def __init__(self, key_paragraphs: List[str], light_action: Tuple[LightSelector, LightPutRequest]):
        self.keys = [[word.lower().strip() for word in p.split()] for p in key_paragraphs]
        self.light_action = light_action

    def is_matching(self, snippet: str) -> bool:
        words = text.filter_non_alnum(snippet).split()
        for lst in self.keys:
            if _are_items_contained_in_order(lst, words):
                return True
        return False

    def __str__(self):
        return ("Action[keys: {}, light_action: ({}, {})]"
                .format(self.keys, self.light_action[0], self.light_action[1]))


class HueActionRegistry:

    def __init__(self, client: HueClient, actions_path: str):
        self.client = client
        self.actions_path = actions_path
        self.actions = {}

    def load_actions(self) -> Dict[str, Action]:
        actions = {}
        if not os.path.exists(self.actions_path):
            LOGGER.warning("No actions defined at " + self.actions_path)
            return {}
        for action_path in os.scandir(self.actions_path):
            abs_path: Path = Path(self.actions_path).joinpath(action_path.path)
            loaded_action = _load_action(str(abs_path))
            actions[action_path.name] = loaded_action
        LOGGER.info("Loaded actions: " + str(len(actions)))
        return actions

    def act(self, instruction: str) -> bool:
        matching_action = next((action for action in self.actions.values() if action.is_matching(instruction)), None)
        if matching_action:
            LOGGER.info("Found action %s for instruction '%s'", matching_action.keys, instruction)
            self.client.light(matching_action.light_action)
            return True
        else:
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
