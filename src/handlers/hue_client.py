import json
from http.client import HTTPResponse
from typing import Collection, Any
from urllib.error import URLError
from urllib.request import urlopen, Request

from src.actions.action import ActionHandler
from src.handlers.lights import Light, LightAction, State

ALL_LIGHTS_ID = "ALL"
LIGHT_ID_STRING_DELIMITER = ","
_DUMMY_RESPONSE_JSON = json.loads("""
{
  "1": {
    "state": { "on": true, "bri": 128, "hue": 8000, "sat": 200 },
    "name": "Living Room Lamp",
    "type": "Extended color light"
  },
  "2": {
    "state": { "on": true, "bri": 254, "hue": 40000, "sat": 100 },
    "name": "Desk Lamp",
    "type": "Extended color light"
  },
  "3": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Bedroom Light",
    "type": "Extended color light"
  },
  "4": {
    "state": { "on": true, "bri": 128, "hue": 8000, "sat": 200 },
    "name": "Living Room Entry",
    "type": "Extended color light"
  },
  "5": {
    "state": { "on": true, "bri": 200, "hue": 35000, "sat": 150 },
    "name": "Living Room Couch",
    "type": "Extended color light"
  },
  "6": {
    "state": { "on": true, "bri": 254, "hue": 40000, "sat": 100 },
    "name": "Living Room Ceiling",
    "type": "Extended color light"
  },
  "7": {
    "state": { "on": true, "bri": 90, "hue": 10000, "sat": 180 },
    "name": "Living Room Table",
    "type": "Extended color light"
  },
  "8": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Living Room Desk",
    "type": "Extended color light"
  },
  "9": {
    "state": { "on": true, "bri": 150, "hue": 5000, "sat": 220 },
    "name": "Kitchen",
    "type": "Extended color light"
  },
  "10": {
    "state": { "on": true, "bri": 100, "hue": 30000, "sat": 130 },
    "name": "Floor 1",
    "type": "Extended color light"
  },
  "11": {
    "state": { "on": true, "bri": 75, "hue": 20000, "sat": 160 },
    "name": "Floor 2",
    "type": "Extended color light"
  },
  "12": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Bedroom Ceiling",
    "type": "Extended color light"
  },
  "13": {
    "state": { "on": true, "bri": 180, "hue": 12000, "sat": 90 },
    "name": "Bedroom Nightstand Alex",
    "type": "Extended color light"
  },
  "14": {
    "state": { "on": true, "bri": 220, "hue": 45000, "sat": 120 },
    "name": "Bedroom Nightstand Jenny",
    "type": "Extended color light"
  }
}
""")


def _from_api_state(api: dict[str, Any]) -> State:
    return State(
        on=api.get("on"),
        hue=round(api["hue"] * 360 / 65535) if "hue" in api else None,
        sat=round(api["sat"] * 100 / 254) if "sat" in api else None,
        bri=round(api["bri"] * 100 / 254) if "bri" in api else None,
    )


def _to_api_state(state: State) -> dict[str, bool | int]:
    result = {}
    if state.on is not None:
        result["on"] = state.on
    if state.hue is not None:
        result["hue"] = round(state.hue * 65535 / 360)
    if state.sat is not None:
        result["sat"] = round(state.sat * 254 / 100)
    if state.bri is not None:
        result["bri"] = max(1, round(state.bri * 254 / 100))
    return result


def _map_to_lights(raw_lights: dict[str, Any]) -> dict[str, Light]:
    return {
        light_id: Light(
            id=light_id,
            name=light["name"],
            state=_from_api_state(light["state"])
        )
        for light_id, light in raw_lights.items()
        if "name" in light and "state" in light
    }


class HueClient(ActionHandler):

    accepted_type = "hue"

    def __init__(self, **kwargs):
        super().__init__()
        self.host = kwargs["host"]
        self.user = kwargs["user"]
        self.actions_path = kwargs["lurker_home"] + "/actions"

        self.lights = {}

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
                http_request = to_http_request(action.state, self.host, self.user, light_id)
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
            self._logger.info(f"Skipping non-light action: type={type(action)}, action={action}")
            return 0

    def _handle_internal(self, light_actions: list[LightAction]) -> int:
        if len(self.lights) < 1:
            self.lights = self._retrieve_lights()
        return self._light(light_actions)

    def get_state(self) -> dict[str, Any]:
        """
        :return: The current state of the lights as JSON string.
        """
        self.lights = self._retrieve_lights()
        return _map_to_lights(self.lights)


def to_http_request(state: State, host: str, user: str, light_id: str) -> Request:
    url = f"http://{host}/api/{user}/lights/{light_id}/state"
    data = json.dumps(_to_api_state(state)).encode("ascii")
    return Request(url, method="PUT", data=data)







