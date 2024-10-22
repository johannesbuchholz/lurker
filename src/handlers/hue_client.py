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
        data = json.dumps({k: v for k, v in self.state.items() if v is not None}).encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return str({k: v for k, v in self.state.items() if v is not None})

class LightAction:

    def __init__(self, light_ids: Collection[str], state: LightState):
        self.light_ids = light_ids
        self.state = state

    def __str__(self):
        return f"{self.__class__.__name__}[ids={self.light_ids}, state={self.state}]"

    def __repr__(self):
        return self.__str__()


class HueClient(ActionHandler):

    _special_commands: Dict[str, Callable[[Match[str]], None]] = {"EXIT": exit}

    def __init__(self, host: str, user: str):
        super().__init__()
        self.host = host
        self.user = user
        self.lights = self._retrieve_lights()

    # TODO: Implement this method
    def _save_current_lights_as_action(self, file_name: str) -> None:
        raise RuntimeError()


    def _retrieve_lights(self) -> Dict[str, Any]:
        url = f"http://{self.host}/api/{self.user}/lights"
        try:
            response: HTTPResponse = urlopen(url)
            body = response.read()
            if response.status != 200:
                raise URLError(f"Response status was not OK (200): response={body}")
        except Exception as e:
            self._logger.error(f"Could not retrieve lights from {self.host}: {str(e)}")
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
                    self._logger.error(f"Could not send light request to light: request={http_request}, light_id={light_id}, msg={str(e)}", exc_info=e)

    def handle(self, action: Action, key_match: Match[str]) -> bool:
        command = action.command
        if type(command) is str:
            callable_command = HueClient._special_commands.get(command, None)
            if callable_command is not None:
                self._logger.info(f"Handling special command: {command}")
                callable_command(key_match)
                return True
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
