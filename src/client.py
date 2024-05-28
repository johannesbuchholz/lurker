import json
from http.client import HTTPResponse
from typing import Optional, Union, Tuple, Collection
from urllib.error import URLError
from urllib.request import urlopen, Request

from src import log
from src import utils

HOST = "host"
USER = "user"
REQUIRED_CONFIG_VALUES = {"host", "user"}


LOGGER = log.new_logger("Lurker ({})".format(__name__))


class LightSelector:

    ALL = "ALL"

    def __init__(self, ids: Union[str, Collection[str]]):
        self.ids = ids

    def select(self, available_ids: Collection[str]) -> Collection[str]:
        if self.ids == LightSelector.ALL:
            return available_ids

        return self.ids

    def __str__(self):
        return str(self.ids)


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
        return "LightPutRequest[{}]".format(self.keyvalues)


class HueClient:

    def __init__(self):
        self._load_config()
        self._retrieve_lights()

    def _load_config(self) -> None:
        with open(utils.get_abs_path("../config.json")) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)

        if not REQUIRED_CONFIG_VALUES.issubset(cfg.keys()):
            raise ValueError("Could not find required config values: " + str(REQUIRED_CONFIG_VALUES))
        self.host = cfg[HOST]
        self.user = cfg[USER]

    def _retrieve_lights(self) -> None:
        url = "http://{}/api/{}/lights".format(self.host, self.user)
        try:
            response: HTTPResponse = urlopen(url)
            if response.status != 200:
                raise URLError("response status was not OK (200): response={}".format(response.read()))
        except URLError as e:
            LOGGER.error("Could not retrieve lights info", exc_info=e)
            return
        except Exception as e:
            LOGGER.error("Unexpected exception", exc_info=e)
            return

        self.lights: dict = json.loads(response.read())
        self.light_ids = self.lights.keys()

    def light(self, light_action: Tuple[LightSelector, LightPutRequest]):
        LOGGER.debug("Sending request: %s", light_action)
        light_selector, request = light_action
        try:
            selected_ids = light_selector.select(self.light_ids)
        except AttributeError:
            LOGGER.warning("Can not send request: light ids have not been initialized")
            return
        for light_id in selected_ids:
            response = urlopen(request.to_http_request(self.host, self.user, light_id))
            LOGGER.info("Request response: " + str(response.read()))
