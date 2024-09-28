import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Dict

from src import log

LURKER_KEYWORD = "LURKER_KEYWORD"
LURKER_MODEL = "LURKER_MODEL"
LURKER_LOG_LEVEL = "LURKER_LOG_LEVEL"
LURKER_USER = "LURKER_USER"
LURKER_HOST = "LURKER_HOST"
LURKER_INPUT_DEVICE = "LURKER_INPUT_DEVICE"
LURKER_OUTPUT_DEVICE = "LURKER_OUTPUT_DEVICE"
LURKER_LANGUAGE = "LURKER_LANGUAGE"
LURKER_SPEECH_CONFIG = "LURKER_SPEECH_CONFIG"

LOGGER = log.new_logger(__name__)


def _get_envs() -> Dict[str, str]:
    envs = {
        LURKER_HOST: os.environ.get(LURKER_HOST),
        LURKER_USER: os.environ.get(LURKER_USER),
        LURKER_LOG_LEVEL: os.environ.get(LURKER_LOG_LEVEL),
        LURKER_MODEL: os.environ.get(LURKER_MODEL),
        LURKER_KEYWORD: os.environ.get(LURKER_KEYWORD),
        LURKER_INPUT_DEVICE: os.environ.get(LURKER_INPUT_DEVICE),
        LURKER_OUTPUT_DEVICE: os.environ.get(LURKER_OUTPUT_DEVICE),
        LURKER_LANGUAGE: os.environ.get(LURKER_LANGUAGE),
        LURKER_SPEECH_CONFIG: os.environ.get(LURKER_SPEECH_CONFIG),
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

@dataclass(frozen=True)
class SpeechConfig:
    instruction_queue_length_seconds: float = 3.
    keyword_queue_length_seconds: float = 1.2
    min_silence_threshold: int = 600
    queue_check_interval_seconds: float = 0.1
    speech_bucket_count: int = 60
    required_leading_silence_ratio: float = 0.1
    required_speech_ratio: float = 0.15
    required_trailing_silence_ratio: float = 0.2

@dataclass(frozen=True)
class LurkerConfig:
    LURKER_MODEL: str = "tiny.pt"
    LURKER_INPUT_DEVICE: str = None
    LURKER_OUTPUT_DEVICE: str = None
    LURKER_USER: str = None
    LURKER_HOST: str = None
    LURKER_KEYWORD: str = "hey john"
    LURKER_LOG_LEVEL: str = "INFO"
    LURKER_LANGUAGE: str = "en"
    LURKER_SPEECH_CONFIG: SpeechConfig = field(default_factory=SpeechConfig)

    def to_pretty_str(self) -> str:
        key_value_strings = ["{}={}".format(field_name, value) for field_name, value in dataclasses.asdict(self).items()]
        return "\n".join(key_value_strings)

def load_lurker_config(config_path: str) -> LurkerConfig:
    config_param_dict:dict = _load_config_file(config_path) | _get_envs()
    if LURKER_SPEECH_CONFIG in config_param_dict:
        # modify param dict to actually contain the nested dataclass object
        speech_config_param_value = config_param_dict[LURKER_SPEECH_CONFIG]
        if type(speech_config_param_value) is not dict:
            # transform param value to a string and try to load it as a dictionary
            speech_config_param_value = json.loads(str(speech_config_param_value))
        config_param_dict[LURKER_SPEECH_CONFIG] = SpeechConfig(**speech_config_param_value)

    return LurkerConfig(**config_param_dict)