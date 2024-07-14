import json
import os
from typing import Dict

from src import log

LURKER_KEYWORD = "LURKER_KEYWORD"
LURKER_MODEL = "LURKER_MODEL"
LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS = "LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS"
LURKER_KEYWORD_QUEUE_LENGTH_SECONDS = "LURKER_KEYWORD_QUEUE_LENGTH_SECONDS"
LURKER_LOG_LEVEL = "LURKER_LOG_LEVEL"
LURKER_USER = "LURKER_USER"
LURKER_HOST = "LURKER_HOST"
LURKER_HOME = "LURKER_HOME"
LURKER_INPUT_DEVICE = "LURKER_INPUT_DEVICE"
LURKER_OUTPUT_DEVICE = "LURKER_OUTPUT_DEVICE"

LOGGER = log.new_logger("Lurker ({})".format(__name__))


def _get_defaults() -> Dict[str, str]:
    return {
        LURKER_HOME: os.getcwd(),
        LURKER_HOST: "",
        LURKER_USER: "",
        LURKER_LOG_LEVEL: "INFO",
        LURKER_KEYWORD_QUEUE_LENGTH_SECONDS: "0.8",
        LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS: "3",
        LURKER_MODEL: "tiny",
        LURKER_KEYWORD: "",
        LURKER_INPUT_DEVICE: "",
        LURKER_OUTPUT_DEVICE: "",
    }


def _get_envs() -> Dict[str, str]:
    envs = {
        LURKER_HOME: os.environ.get(LURKER_HOME),
        LURKER_HOST: os.environ.get(LURKER_HOST),
        LURKER_USER: os.environ.get(LURKER_USER),
        LURKER_LOG_LEVEL: os.environ.get(LURKER_LOG_LEVEL),
        LURKER_KEYWORD_QUEUE_LENGTH_SECONDS: os.environ.get(LURKER_KEYWORD_QUEUE_LENGTH_SECONDS),
        LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS: os.environ.get(LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS),
        LURKER_MODEL: os.environ.get(LURKER_MODEL),
        LURKER_KEYWORD: os.environ.get(LURKER_KEYWORD),
        LURKER_INPUT_DEVICE: os.environ.get(LURKER_INPUT_DEVICE),
        LURKER_OUTPUT_DEVICE: os.environ.get(LURKER_OUTPUT_DEVICE),
    }
    return {key: value for key, value in envs.items() if value is not None}


def _load_config_file(path: str) -> Dict[str, str]:
    try:
        with open(path) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)
    except Exception as e:
        LOGGER.warning("Could not load configuration file from %s: %s", path, e)
        cfg = {}
    return cfg


class _LurkerConfig:

    def __init__(self):
        defaults = _get_defaults()
        envs = _get_envs()
        lurker_home = envs.get(LURKER_HOME, defaults[LURKER_HOME])
        config = _load_config_file(lurker_home + "/config.json")
        self._config = defaults | config | envs

    def host(self) -> str:
        return self._config[LURKER_HOST]

    def user(self) -> str:
        return self._config[LURKER_USER]

    def home(self) -> str:
        return self._config[LURKER_HOME]

    def log_level(self) -> str:
        return self._config[LURKER_LOG_LEVEL]

    def output_device(self) -> str:
        return self._config[LURKER_OUTPUT_DEVICE]

    def keyword_queue_length_seconds(self) -> float:
        return float(self._config[LURKER_KEYWORD_QUEUE_LENGTH_SECONDS])

    def instruction_queue_length_seconds(self) -> float:
        return float(self._config[LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS])

    def model(self) -> str:
        return self._config[LURKER_MODEL]

    def keyword(self) -> str:
        return self._config[LURKER_KEYWORD]
    
    def input_device(self) -> str:
        return self._config[LURKER_INPUT_DEVICE]

    def __str__(self):
        return "\n".join(
            ["{}={}".format(name, value) for name, value in (self._config | {LURKER_USER: "***"}).items()])


CONFIG = _LurkerConfig()
