import json
import logging
from http.client import HTTPResponse
from typing import Optional, Union, Tuple, List, Callable, Collection
from urllib.request import urlopen, Request

from log import logger

HOST = "host"
USER = "user"
REQUIRED_CONFIG_VALUES = {"host", "user"}


class LightSelector:

    def __init__(self, id_selector: Union[int, Callable[[Collection[int]], List[int]]]):
        self.id_selector = id_selector

    def select(self, ids: Collection[int]) -> List[int]:
        if isinstance(self.id_selector, int):
            if self.id_selector in ids:
                return [self.id_selector]
            else:
                return []
        return self.id_selector(ids)


class LightPutRequest:

    def __init__(self,
                 on: Optional[bool] = None,
                 sat: Optional[int] = None,
                 bri: Optional[int] = None,
                 hue: Optional[int] = None):
        self.keyvalues = {"on": on, "sat": sat, "bri": bri, "hue": hue}

    def to_http_request(self, host: str, user: str, light_id: int) -> Request:
        url = "http://{}/api/{}/lights_info/{}/state".format(host, user, light_id)
        data = json.dumps({k: v for k, v in self.keyvalues.items() if v}).encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return "LightPutRequest{keyvalues={}}".format(self.keyvalues)


class HueClient:

    def __init__(self):
        self._load_config()
        # self._retrieve_lights_info() # TODO: Comment in when config is correctly set

    def _load_config(self) -> None:
        with open("config.json") as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)

        if not REQUIRED_CONFIG_VALUES.issubset(cfg.keys()):
            raise ValueError("Could not find required config values: " + str(REQUIRED_CONFIG_VALUES))
        self.host = cfg[HOST]
        self.user = cfg[USER]

    def _retrieve_lights_info(self) -> None:
        url = "http://%s/api/%s/lights".format(self.host, self.user)
        response: HTTPResponse = json.loads(urlopen(url))
        if response.status != 200:
            raise IOError("Could not initialize: response={}".format(response.read()))
        self.lights_info: dict = json.loads(response.read())
        self.light_ids = self.lights_info.keys()

    def light(self, light_action: Tuple[LightSelector, LightPutRequest]):
        logger.debug("Sending request: %s", light_action)
        light_selector, request = light_action
        for light_id in light_selector.select(self.light_ids):
            response = urlopen(request.to_http_request(self.host, self.user, light_id))
            if response.info != 200:
                logging.error("Failed request: " + response.read())
