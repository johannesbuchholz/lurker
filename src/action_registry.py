import json
import os
from typing import List, Iterable, Tuple

from src import log, utils
from src.client import HueClient, LightPutRequest, LightSelector
from src.utils import filter_non_alnum

LOGGER = log.new_logger("Lurker ({})".format(__name__))


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
        words = filter_non_alnum(snippet).split()
        for lst in self.key_paragraph_lists:
            if _are_items_contained_in_order(lst, words):
                return True
        return False

    def __str__(self):
        return ("Action[keys: {}, light_action: ({}, {})]"
                .format(self.keys, self.light_action[0], self.light_action[1]))


def load_actions() -> List[Action]:
    actions_path = utils.get_abs_path("resources/actions")
    actions = []
    for action_path in os.scandir(actions_path):
        with open(utils.get_abs_path(action_path.path)) as action_file_handle:
            action_dict: dict = json.load(action_file_handle)
            action = Action(
                key_paragraphs=action_dict["keys"],
                light_action=(LightSelector(action_dict["lights"]), LightPutRequest(**action_dict["request"])))
            LOGGER.info("Loaded action: %s", action)
            actions.append(action)
    return actions


class HueActionRegistry:

    def __init__(self, client: HueClient):
        self.client = client
        self.actions: List[Action] = load_actions()
        LOGGER.info("Loaded %s light actions", len(self.actions))

    def act(self, instruction: str) -> bool:
        matching_action = next((action for action in self.actions if action.is_matching(instruction)), None)
        if matching_action:
            LOGGER.info("Found action %s for instruction '%s'", matching_action.keys, instruction)
            self.client.light(matching_action.light_action)
            return True
        else:
            LOGGER.info("Could not find action for instruction '%s'", instruction)
            return False
