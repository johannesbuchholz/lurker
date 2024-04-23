from typing import List, Iterable, Tuple

from src import log
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
        self.key_paragraph_lists = [[word.lower().strip() for word in p.split()] for p in key_paragraphs]
        self.light_action = light_action

    def is_matching(self, snippet: str) -> bool:
        words = filter_non_alnum(snippet).split()
        for lst in self.key_paragraph_lists:
            if _are_items_contained_in_order(lst, words):
                return True
        return False


class HueActionRegistry:

    def __init__(self, client: HueClient):
        self.client = client
        self.actions: List[Action] = [x for x in globals().values() if isinstance(x, Action)]
        LOGGER.info("Loaded %s light actions", len(self.actions))

    def act(self, instruction: str) -> bool:
        matching_action = next((action for action in self.actions if action.is_matching(instruction)), None)
        if matching_action:
            LOGGER.info("Found action %s for instruction '%s'", matching_action.key_paragraph_lists, instruction)
            self.client.light(matching_action.light_action)
            return True
        else:
            LOGGER.info("Could not find action for instruction '%s'", instruction)
            return False


# ---------- ADDITIONAL ACTIONS ARE PUT HERE

ALL: LightSelector = LightSelector(lambda ids: ids)

ALL_LIGHTS_OUT = Action(key_paragraphs=["all lights out", "all lights off", "make it dark", "the lights off", "licht aus"],
                        light_action=(ALL, LightPutRequest(on=False)))
ALL_LIGHTS_ON = Action(key_paragraphs=["all lights on", "the lights on", "make it bright", "licht an"],
                       light_action=(ALL, LightPutRequest(on=True)))
ALL_LIGHTS_BLUE = Action(key_paragraphs=["alles blau"],
                       light_action=(ALL, LightPutRequest(on=True, sat=89, bri=48, hue=192)))
