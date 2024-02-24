import json
import logging
from enum import Enum
from http.client import HTTPResponse
from typing import Optional, Union
from urllib.request import urlopen, Request

from log import logger

HOST = "host"
USER = "user"
REQUIRED_CONFIG_VALUES = {"host", "user"}


class LightGroup(Enum):
    ALL = -1


class Lights:

    def __init__(self, host: str, user: str):
        self.host = host
        self.user = user
        # TODO: Comment in when config is correctly set
        # self._retrieve_lights_info()

    def _retrieve_lights_info(self) -> None:
        url = "http://%s/api/%s/lights".format(self.host, self.user)
        response: HTTPResponse = json.loads(urlopen(url))
        if response.status != 200:
            raise IOError("Could not initialize: response={}".format(response.read()))
        self.info: dict = json.loads(response.read())
        self.light_ids = self.info.keys()


class LightPutRequest:

    def __init__(self,
                 light_id: Union[int, LightGroup],
                 on: Optional[bool] = None,
                 sat: Optional[int] = None,
                 bri: Optional[int] = None,
                 hue: Optional[int] = None):
        self.light_id = light_id
        self.keyvalues = {"on": on, "sat": sat, "bri": bri, "hue": hue}

    def to_http_request(self, host: str, user: str) -> Request:
        url = "http://{}/api/{}/info/{}/state".format(host, user, self.light_id)
        data = json.dumps({k: v for k, v in self.keyvalues.items() if v}).encode("ascii")
        return Request(url, method="PUT", data=data)

    def __str__(self):
        return "LightPutRequest{light_id={}, keyvalues={}}".format(self.light_id, self.keyvalues)


class HueClient:

    def __init__(self):
        self._load_config()
        self.lights_client = Lights(self.host, self.user)

    def _load_config(self) -> None:
        with open("config.json") as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)

        if not REQUIRED_CONFIG_VALUES.issubset(cfg.keys()):
            raise ValueError("Could not find required config values: " + str(REQUIRED_CONFIG_VALUES))
        self.host = cfg[HOST]
        self.user = cfg[USER]

    def send(self, request: LightPutRequest):
        logger.debug("Sending request: %s", request)
        response = urlopen(request.to_http_request(self.host, self.user))
        if response.info != 200:
            logging.error("Failed request: " + response.read())
