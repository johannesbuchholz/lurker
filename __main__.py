import json

from src import log
from src.action_registry import HueActionRegistry
from src.client import HueClient
from src.speech import SpeechToTextListener
from src.utils import Constants

LOGGER = log.new_logger("Lurker ({})".format(__name__))


class LurkerConfig:

    def __init__(self, **kwargs):
        self.host = kwargs.get("host")
        self.user = kwargs.get("user")
        self.keyword = kwargs.get("keyword") or ""

    def __str__(self):
        return "LurkerConfig[host={}, user=***, keyword={}]".format(self.host, self.keyword)


def _load_config(path: str) -> LurkerConfig:
    try:
        with open(path) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)
    except Exception as e:
        LOGGER.warning("Could not load configuration: " + str(e), exc_info=e)
        cfg = {}
    return LurkerConfig(**cfg)


def _print_constants():
    LOGGER.info("LURKER_LOG_LEVEL: %s", Constants.LURKER_LOG_LEVEL)
    LOGGER.info("LURKER_ENABLE_DYNAMIC_CONFIGURATION: %s", Constants.LURKER_ENABLE_DYNAMIC_CONFIGURATION)
    LOGGER.info("LURKER_HOME: %s", Constants.LURKER_HOME)
    LOGGER.info("LURKER_KEYWORD: %s", Constants.LURKER_KEYWORD)
    LOGGER.info("LURKER_SOUND_TOOL: %s", Constants.LURKER_SOUND_TOOL)
    LOGGER.info("KEYWORD_QUEUE_LENGTH_SECONDS: %s", Constants.KEYWORD_QUEUE_LENGTH_SECONDS)
    LOGGER.info("INSTRUCTION_QUEUE_LENGTH_SECONDS: %s", Constants.INSTRUCTION_QUEUE_LENGTH_SECONDS)


if __name__ == "__main__":
    _print_constants()

    config_path = Constants.LURKER_HOME + "/config.json"
    LOGGER.info("Loading configuration from %s", config_path)
    config = _load_config(config_path)
    LOGGER.info("Loaded configuration: %s", config)

    LOGGER.info("Setting up connection to hue")
    hue_client = HueClient(config.host, config.user)
    registry = HueActionRegistry(hue_client)

    LOGGER.info("Start listening...")
    listener = SpeechToTextListener(instruction_callback=lambda instruction: registry.act(instruction))
    listener.start_listening(keyword=Constants.LURKER_KEYWORD or config.keyword)

    LOGGER.info("Press any key to quit.")
    input()
    LOGGER.info("Quitting lurker...")
    exit(0)