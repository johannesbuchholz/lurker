import json
from http.client import HTTPResponse
from typing import Optional, Union, Collection, Any, Dict, Callable
from urllib.error import URLError
from urllib.request import urlopen, Request

from src.action import ActionHandler, Action


class LightSelector:

    ALL = "ALL"

    def __init__(self, lights: Union[str, Collection[str]]):
        self.lights = lights

    def select(self, available_ids: Collection[str]) -> Collection[str]:
        if self.lights == LightSelector.ALL:
            return available_ids
        return self.lights

    def __str__(self):
        return str(self.lights)


class LightPutRequest:

    def __init__(self,
                 on: Optional[bool] = None,
                 sat: Optional[int] = None,
                 bri: Optional[int] = None,
                 hue: Optional[int] = None):
        self.keyvalues = {"on": on, "sat": sat, "bri": bri, "hue": hue}

    def to_http_request(self, host: str, user: str, light_id: str) -> Request:
        url = f"http://{host}/api/{user}/lights/{light_id}/state"
        data = json.dumps({k: v for k, v in self.keyvalues.items() if v is not None}).encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return str({k: v for k, v in self.keyvalues.items() if v is not None})

class LightAction:
    def __init__(self, lights: Union[str, Collection[str]], request: dict):
        self.selector = LightSelector(lights)
        self.request = LightPutRequest(**request)


class HueClient(ActionHandler):

    _special_commands: Dict[str, Callable[[], None]] = {"EXIT": exit}

    def __init__(self, host: str, user: str):
        super().__init__()
        self.host = host
        self.user = user
        self.lights = {}

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

    def _light(self, light_action: LightAction):
        if len(self.lights) < 1:
            self.lights = self._retrieve_lights()

        self._logger.debug(f"Sending request: selected_lights={light_action.selector}, request={light_action.request}",)
        selected_ids = light_action.selector.select(self.lights.keys())
        if len(selected_ids) == 0:
            self._logger.warning("Can not send request: light ids have not been initialized")
            return
        for light_id in selected_ids:
            http_request = light_action.request.to_http_request(self.host, self.user, light_id)
            try:
                urlopen(http_request)
            except Exception as e:
                self._logger.error(f"Could not send light request to light: request={http_request}, light_id={light_id}, msg={str(e)}", exc_info=e)

    def handle(self, action: Action) -> bool:
        command = action.command
        if type(command) is str:
            callable_command = HueClient._special_commands.get(command, None)
            if callable_command is not None:
                self._logger.info(f"Handling special command: {command}")
                callable_command()
                return True
        return self._handle_internal(action)

    def _handle_internal(self, action: Action) -> bool:
        light_action = LightAction(**action.command)
        self._light(light_action)
        return True
