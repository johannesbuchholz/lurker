from typing import List, Iterable, Optional

from client import HueClient, LightPutRequest
from log import logger


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

    def __init__(self, key_paragraphs: List[str], light_action: Optional[LightPutRequest]):
        self.key_paragraph_lists = {[word.lower().strip() for word in p.split()] for p in key_paragraphs}
        self.light_action = light_action

    def is_matching(self, snippet: str) -> bool:
        words = snippet.lower().strip().split()
        for lst in self.key_paragraph_lists:
            if _are_items_contained_in_order(lst, words):
                return True
        return False


class HueActionRegistry:

    def __init__(self, client: HueClient):
        self.client = client
        self.actions: List[Action] = []  # TODO: somehow load actions

    def act(self, instruction: str) -> None:
        matching_action = next((a for a in self.actions if a.is_matching(instruction)), None)
        if matching_action:
            logger.info("Found action %s for instruction '%s'", matching_action.key_paragraph_lists, instruction)
            self.client.send(matching_action.light_action)
        else:
            logger.info("Could not find action for instruction '%s'", instruction)


