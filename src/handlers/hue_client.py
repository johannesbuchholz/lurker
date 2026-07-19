import json
from http.client import HTTPResponse
from typing import Collection, Any, Match
from urllib.error import URLError
from urllib.request import urlopen

from src.action import ActionHandler
from src.handlers.lights import LightState, LightAction

ALL_LIGHTS_ID = "ALL"
LIGHT_ID_STRING_DELIMITER = ","

class HueClient(ActionHandler):

    accepted_type = "hue"

    def __init__(self, **kwargs):
        super().__init__()
        self.host = kwargs["host"]
        self.user = kwargs["user"]
        self.actions_path = kwargs["lurker_home"] + "/actions"

        self.lights = {}

    def _save_current_lights_as_action(self, key_match: Match) -> int:
        try:
            action_key = key_match.group(1)
        except IndexError as e:
            self._logger.warning(f"Unable to save current light state: Could not extract group '1' in match {key_match}: {e}")
            return 1

        if len(action_key) < 1:
            self._logger.warning(f"Unable to save current light state: Extracted action key is empty: key_match={key_match}")
            return 1

        file_name_suffix = action_key.replace(" ", "_").lower()
        lights = self._retrieve_lights()
        if len(lights) < 1:
            self._logger.warning("No light ids available. Abort saving current light settings.")
            return 1

        light_action_dict = {light_id: LightState(**light["state"]).to_dict() for light_id, light in lights.items() if "state" in light}
        action_dict = {"keys": [action_key], "command": light_action_dict}
        file_path = self.actions_path + f"/{self.__class__.__name__}_saved_{file_name_suffix}.json"
        with open(file_path, "w") as file_handle:
            json.dump(action_dict, file_handle, indent=2)
        self._logger.info(f"Wrote action to {file_path}: {action_dict}")
        return 0

    def _retrieve_lights(self) -> dict[str, Any]:
        url = f"http://{self.host}/api/{self.user}/lights"
        try:
            response: HTTPResponse = urlopen(url, timeout=8.)
            body = response.read()
            if response.status != 200:
                raise URLError(f"Response status was not OK (200): response={body}")
        except Exception as e:
            self._logger.warning(f"Could not retrieve lights from {self.host}: {str(e)}")
            return {}
        self._logger.debug(f"Retrieved light info: {body}")
        light_dict:dict = json.loads(body)
        self._logger.info(f"Available lights: {light_dict.keys()}")
        return light_dict

    def _light(self, light_actions: Collection[LightAction]) -> int:
        self._logger.info(f"Applying light actions: {light_actions}")
        if len(self.lights) < 1:
            self._logger.warning("Can not send request: light ids have not been initialized")
            return 1
        for action in light_actions:
            for light_id in action.light_ids:
                http_request = action.state.to_http_request(self.host, self.user, light_id)
                self._logger.debug(f"Sending request: {http_request.get_method()} {http_request.data}")
                try:
                    urlopen(http_request, timeout=4.)
                except Exception as e:
                    self._logger.error(f"Could not send light request: request_data={http_request.data}, light_id={light_id}, msg={str(e)}", exc_info=e)
        return 0

    def handle(self, action) -> int:
        if action is list[LightAction]:
            return self._handle_internal(action)
        else:
            self._logger.info(f"Skipping non-light action: {action}")
            return 0

    def _handle_internal(self, light_actions: list[LightAction]) -> int:
        if len(self.lights) < 1:
            self.lights = self._retrieve_lights()
        return self._light(light_actions)
