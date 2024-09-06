import json
import os
from typing import Dict, Optional

from src import log

LURKER_KEYWORD = "LURKER_KEYWORD"
LURKER_MODEL = "LURKER_MODEL"
LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS = "LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS"
LURKER_KEYWORD_QUEUE_LENGTH_SECONDS = "LURKER_KEYWORD_QUEUE_LENGTH_SECONDS"
LURKER_LOG_LEVEL = "LURKER_LOG_LEVEL"
LURKER_USER = "LURKER_USER"
LURKER_HOST = "LURKER_HOST"
LURKER_SILENCE_THRESHOLD = "LURKER_SILENCE_THRESHOLD"
LURKER_INPUT_DEVICE = "LURKER_INPUT_DEVICE"
LURKER_OUTPUT_DEVICE = "LURKER_OUTPUT_DEVICE"

LOGGER = log.new_logger(__name__)


def _get_envs() -> Dict[str, str]:
    envs = {
        LURKER_HOST: os.environ.get(LURKER_HOST),
        LURKER_USER: os.environ.get(LURKER_USER),
        LURKER_LOG_LEVEL: os.environ.get(LURKER_LOG_LEVEL),
        LURKER_KEYWORD_QUEUE_LENGTH_SECONDS: os.environ.get(LURKER_KEYWORD_QUEUE_LENGTH_SECONDS),
        LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS: os.environ.get(LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS),
        LURKER_MODEL: os.environ.get(LURKER_MODEL),
        LURKER_KEYWORD: os.environ.get(LURKER_KEYWORD),
        LURKER_SILENCE_THRESHOLD: os.environ.get(LURKER_SILENCE_THRESHOLD),
        LURKER_INPUT_DEVICE: os.environ.get(LURKER_INPUT_DEVICE),
        LURKER_OUTPUT_DEVICE: os.environ.get(LURKER_OUTPUT_DEVICE),
    }
    return {key: value for key, value in envs.items() if value is not None}


def _get_defaults() -> Dict[str, Optional[str]]:
    return {
        LURKER_LOG_LEVEL: "INFO",
        LURKER_KEYWORD_QUEUE_LENGTH_SECONDS: "1.2",
        LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS: "3.",
        LURKER_MODEL: "tiny",
        LURKER_SILENCE_THRESHOLD: "1800",
    }


def _load_config_file(path: str) -> Dict[str, str]:
    try:
        with open(path) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)
    except Exception as e:
        LOGGER.warning("Could not load configuration file from %s: %s", path, e)
        cfg = {}
    return cfg


class LurkerConfig:

    def __init__(self, config_path: str):
        self._config = _get_defaults() | _get_envs() | _load_config_file(config_path)

    def host(self) -> Optional[str]:
        return self._config.get(LURKER_HOST)

    def user(self) -> Optional[str]:
        return self._config.get(LURKER_USER)

    def log_level(self) -> str:
        return self._config.get(LURKER_LOG_LEVEL)

    def silence_threshold(self) -> int:
        return int(self._config.get(LURKER_SILENCE_THRESHOLD))

    def input_device(self) -> Optional[str]:
        return self._config.get(LURKER_INPUT_DEVICE)

    def output_device(self) -> Optional[str]:
        return self._config.get(LURKER_OUTPUT_DEVICE)

    def keyword_queue_length_seconds(self) -> float:
        return float(self._config.get(LURKER_KEYWORD_QUEUE_LENGTH_SECONDS))

    def instruction_queue_length_seconds(self) -> float:
        return float(self._config.get(LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS))

    def model(self) -> str:
        return self._config.get(LURKER_MODEL)

    def keyword(self) -> Optional[str]:
        return self._config.get(LURKER_KEYWORD)

    def __str__(self):
        return "\n".join(
            ["{}={}".format(name, value) for name, value in (self._config | {LURKER_USER: "***"}).items()])
