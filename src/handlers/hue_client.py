import json
from http.client import HTTPResponse
from typing import Collection, Any, Dict, Callable, Match, List
from urllib.error import URLError
from urllib.request import urlopen, Request

from src.action import ActionHandler, Action

ALL_LIGHTS_ID = "ALL"
LIGHT_ID_STRING_DELIMITER = ","

class LightState:

    ALLOWED_LIGHT_KEYS = ["on", "sat", "bri", "hue"]

    def __init__(self, **kwargs):
        self.state = {k: v for k, v in kwargs.items() if k in LightState.ALLOWED_LIGHT_KEYS}

    def to_http_request(self, host: str, user: str, light_id: str) -> Request:
        url = f"http://{host}/api/{user}/lights/{light_id}/state"
        data = self.to_json().encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return str(self.to_dict())

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> Dict[str, str]:
        return {k: v for k, v in self.state.items() if v is not None}

class LightAction:

    def __init__(self, light_ids: Collection[str], state: LightState):
        self.light_ids = light_ids
        self.state = state

    def __str__(self):
        return f"{self.__class__.__name__}[ids={self.light_ids}, state={self.state}]"

    def __repr__(self):
        return self.__str__()

class HueClient(ActionHandler):

    def __init__(self, **kwargs):
        super().__init__()
        self.host = kwargs["host"]
        self.user = kwargs["user"]
        self.actions_path = kwargs["lurker_home"] + "/actions"

        self.lights = {}
        self._special_commands: Dict[str, Callable[[Match[str]], bool]] = {
            "EXIT": lambda key_match: exit(0),
            "SAVE": self._save_current_lights_as_action
        }

    def _save_current_lights_as_action(self, key_match: Match) -> bool:
        try:
            action_key = key_match.group(1)
        except IndexError as e:
            self._logger.warning(f"Unable to save current light state: Could not extract group '1' in match {key_match}: {e}")
            return False

        if len(action_key) < 1:
            self._logger.warning(f"Unable to save current light state: Extracted action key is empty: key_match={key_match}")
            return False

        file_name_suffix = action_key.replace(" ", "_").lower()
        lights = self._retrieve_lights()
        light_action_dict = {light_id: LightState(**light["state"]).to_dict() for light_id, light in lights.items() if "state" in light}
        action_dict = {"keys": [action_key], "command": light_action_dict}
        file_path = self.actions_path + f"/{self.__class__.__name__}_saved_{file_name_suffix}.json"
        with open(file_path, "w") as file_handle:
            json.dump(action_dict, file_handle, indent=2)
        self._logger.info(f"Wrote action to {file_path}: {action_dict}")
        return True

    def _retrieve_lights(self) -> Dict[str, Any]:
        url = f"http://{self.host}/api/{self.user}/lights"
        try:
            response: HTTPResponse = urlopen(url)
            body = response.read()
            if response.status != 200:
                raise URLError(f"Response status was not OK (200): response={body}")
        except Exception as e:
            self._logger.error(f"Could not retrieve lights from {self.host}: {str(e)}", exc_info=e)
            return {}
        self._logger.debug(f"Retrieved light info: {body}")
        light_dict:dict = json.loads(body)
        self._logger.info(f"Available lights: {light_dict.keys()}")
        return light_dict

    def _light(self, light_actions: Collection[LightAction]):
        self._logger.info(f"Applying light actions: {light_actions}")
        if len(self.lights) < 1:
            self._logger.warning("Can not send request: light ids have not been initialized")
            return
        for action in light_actions:
            for light_id in action.light_ids:
                http_request = action.state.to_http_request(self.host, self.user, light_id)
                self._logger.debug(f"Sending request: {http_request.get_method()} {http_request.data}")
                try:
                    urlopen(http_request)
                except Exception as e:
                    self._logger.error(f"Could not send light request to light: request_data={http_request.data}, light_id={light_id}, msg={str(e)}", exc_info=e)

    def handle(self, action: Action, key_match: Match[str]) -> bool:
        command = action.command
        if type(command) is str:
            special_command = self._special_commands.get(command, None)
            if special_command is not None:
                self._logger.info(f"Handling special command with matching key: command={command}, key_match={key_match}")
                return special_command(key_match)
        return self._handle_internal(action)

    def _handle_internal(self, action: Action) -> bool:
        if len(self.lights) < 1:
            self.lights = self._retrieve_lights()

        light_actions: List[LightAction] = []
        for item in action.command.items():
            light_id_string, light_request = item
            if light_id_string == ALL_LIGHTS_ID:
                light_ids = list(self.lights.keys())
            else:
                light_ids = [id_str.strip() for id_str in light_id_string.split(LIGHT_ID_STRING_DELIMITER) if len(id_str) > 0 and not id_str.isspace()]
            light_actions.append(LightAction(light_ids=light_ids, state=LightState(**light_request)))

        self._light(light_actions)
        return True
