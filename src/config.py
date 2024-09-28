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
LURKER_MIN_SILENCE_THRESHOLD = "LURKER_MIN_SILENCE_THRESHOLD"
LURKER_INPUT_DEVICE = "LURKER_INPUT_DEVICE"
LURKER_OUTPUT_DEVICE = "LURKER_OUTPUT_DEVICE"
LURKER_KEYWORD_INTERVAL_SECONDS = "LURKER_KEYWORD_INTERVAL_SECONDS"
LURKER_LANGUAGE = "LURKER_LANGUAGE"

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
        LURKER_MIN_SILENCE_THRESHOLD: os.environ.get(LURKER_MIN_SILENCE_THRESHOLD),
        LURKER_INPUT_DEVICE: os.environ.get(LURKER_INPUT_DEVICE),
        LURKER_OUTPUT_DEVICE: os.environ.get(LURKER_OUTPUT_DEVICE),
        LURKER_KEYWORD_INTERVAL_SECONDS: os.environ.get(LURKER_KEYWORD_INTERVAL_SECONDS),
        LURKER_LANGUAGE: os.environ.get(LURKER_LANGUAGE),
    }
    return {key: value for key, value in envs.items() if value is not None}


def _get_defaults() -> Dict[str, str]:
    return {
        LURKER_LOG_LEVEL: "INFO",
        LURKER_KEYWORD_QUEUE_LENGTH_SECONDS: "1.2",
        LURKER_INSTRUCTION_QUEUE_LENGTH_SECONDS: "3.",
        LURKER_MODEL: "<path not set>",
        LURKER_MIN_SILENCE_THRESHOLD: "800",
        LURKER_KEYWORD_INTERVAL_SECONDS: "0.1",
        LURKER_LANGUAGE: "en"
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

    def min_silence_threshold(self) -> int:
        return int(self._config.get(LURKER_MIN_SILENCE_THRESHOLD))

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
    
    def keyword_interval(self) -> float:
        return float(self._config.get(LURKER_KEYWORD_INTERVAL_SECONDS))
    
    def language(self) -> str:
        return self._config.get(LURKER_LANGUAGE)
    
    def __str__(self):
        key_value_strings = ["{}={}".format("LURKER_" + func.upper(), str(getattr(self, func)())) for func in dir(self) if
                          callable(getattr(self, func)) and not func.startswith("__")]
        return "\n".join(key_value_strings)
