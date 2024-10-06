import json
from http.client import HTTPResponse
from typing import Optional, Union, Collection, Any, Dict
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
        url = "http://{}/api/{}/lights/{}/state".format(host, user, light_id)
        data = json.dumps({k: v for k, v in self.keyvalues.items() if v is not None}).encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return str({k: v for k, v in self.keyvalues.items() if v is not None})

class LightAction:
    def __init__(self, lights: Union[str, Collection[str]], request: dict):
        self.selector = LightSelector(lights)
        self.request = LightPutRequest(**request)


class HueClient(ActionHandler):

    def __init__(self, host: str, user: str):
        super().__init__()
        self.host = host
        self.user = user
        self.lights = self._retrieve_lights()

    def _retrieve_lights(self) -> Dict[str, Any]:
        url = "http://{}/api/{}/lights".format(self.host, self.user)
        try:
            response: HTTPResponse = urlopen(url)
            if response.status != 200:
                raise URLError("Response status was not OK (200): response={}".format(response.read()))
        except Exception as e:
            self._logger.error("Could not retrieve lights from %s: %s", self.host, str(e))
            return {}

        self.lights: dict = json.loads(response.read())

    def _light(self, light_action: LightAction):
        self._logger.debug("Sending request: selected_lights=%s, request=%s", light_action.selector, light_action.request)
        selected_ids = light_action.selector.select(self.lights.keys())
        if len(selected_ids) == 0:
            self._logger.warning("Can not send request: light ids have not been initialized")
            return
        for light_id in selected_ids:
            http_request = light_action.request.to_http_request(self.host, self.user, light_id)
            try:
                urlopen(http_request)
            except Exception as e:
                self._logger.error("Could not send light request to light: request=%s, light_id=%s, msg=%s", http_request, light_id, str(e), exc_info=e)

    def _handle_internal(self, action: Action) -> bool:
        light_action = LightAction(**action.command)
        self._light(light_action)
        return True
