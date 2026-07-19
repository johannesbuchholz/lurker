import json
from typing import Collection
from urllib.request import Request


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

    def to_dict(self) -> dict[str, str]:
        return {k: v for k, v in self.state.items() if v is not None}


class LightAction:

    def __init__(self, light_ids: Collection[str], state: LightState):
        self.light_ids = light_ids
        self.state = state

    def __str__(self):
        return f"{self.__class__.__name__}[ids={self.light_ids}, state={self.state}]"

    def __repr__(self):
        return self.__str__()

def actions_from_json(json_str: str) -> list[LightAction]:
    # TODO: implement. use something like LightState(**light_state) where the input json looks like this
    #  {"0,1,2,3": {"on": true}, "2,3": {"on": false}, "0": {"bri": 50}}`, This should result in 3 LightAction items.
    pass
