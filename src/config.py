import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Union, Optional

from src import log

LURKER_KEYWORD = "LURKER_KEYWORD"
LURKER_MODEL = "LURKER_MODEL"
LURKER_LOG_LEVEL = "LURKER_LOG_LEVEL"
LURKER_LOG_FILE = "LURKER_LOG_FILE"
LURKER_INPUT_DEVICE = "LURKER_INPUT_DEVICE"
LURKER_OUTPUT_DEVICE = "LURKER_OUTPUT_DEVICE"
LURKER_LANGUAGE = "LURKER_LANGUAGE"
LURKER_SPEECH_CONFIG = "LURKER_SPEECH_CONFIG"
LURKER_HANDLER_MODULE = "LURKER_HANDLER_MODULE"
LURKER_HANDLER_CONFIG = "LURKER_HANDLER_CONFIG"
LURKER_ACTION_REFRESH_INTERVAL = "LURKER_ACTION_REFRESH_INTERVAL"

LOGGER = log.new_logger(__name__)


def _get_envs() -> Dict[str, str]:
    envs = {
        LURKER_LOG_LEVEL: os.environ.get(LURKER_LOG_LEVEL),
        LURKER_LOG_FILE: os.environ.get(LURKER_LOG_FILE),
        LURKER_MODEL: os.environ.get(LURKER_MODEL),
        LURKER_KEYWORD: os.environ.get(LURKER_KEYWORD),
        LURKER_INPUT_DEVICE: os.environ.get(LURKER_INPUT_DEVICE),
        LURKER_OUTPUT_DEVICE: os.environ.get(LURKER_OUTPUT_DEVICE),
        LURKER_LANGUAGE: os.environ.get(LURKER_LANGUAGE),
        LURKER_SPEECH_CONFIG: os.environ.get(LURKER_SPEECH_CONFIG),
        LURKER_HANDLER_MODULE: os.environ.get(LURKER_HANDLER_MODULE),
        LURKER_HANDLER_CONFIG: os.environ.get(LURKER_HANDLER_CONFIG),
        LURKER_ACTION_REFRESH_INTERVAL: os.environ.get(LURKER_ACTION_REFRESH_INTERVAL),
    }
    return {key: value for key, value in envs.items() if value is not None}


def _load_config_file(path: str) -> Dict[str, str]:
    if os.path.exists(path):
        with open(path) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)
    else:
        LOGGER.info(f"No configuration file found at {path}")
        cfg = {}
    return cfg


@dataclass(frozen=True)
class SpeechConfig:
    instruction_queue_length_seconds: float = 3.
    """Number of seconds of audio data the instruction buffer queue should hold after the keyword has been detected."""
    keyword_queue_length_seconds: float = 1.2
    """Number of seconds of audio data the keyword buffer queue should hold."""
    min_silence_threshold: int = 600
    """Absolute amplitude value under which a mean amplitude of an audio snippet is considered as silent and is not passed to the transcription engine."""
    queue_check_interval_seconds: float = 0.1
    """Duration in seconds to wait in between checks whether an an audio queue should be passed to the transcription engine."""
    speech_bucket_count: int = 60
    """Number of partitions of an audio queue over which mean amplitudes are computed in order to determine if the respective queue should be sent to the transcription engine."""
    required_leading_silence_ratio: float = 0.1
    """Ratio of leading silent partitions required to consider an audio queue relevant for passing it to the transcription engine."""
    required_speech_ratio: float = 0.15
    """Ratio of non-silent partitions required to consider an audio queue relevant for passing it to the transcription engine."""
    required_trailing_silence_ratio: float = 0.2
    """Ratio of trailing silent partitions required to consider an audio queue relevant for passing it to the transcription engine."""
    ambiance_level_factor: float = 1.5
    """Factor to determine the dynamic silence-threshold based on the mean amplitudes of past keyword-queue evaluations."""
    transcription_timeout_seconds: float = 3
    """Maximum number of seconds to wait for a transcription before aborting."""


@dataclass(frozen=True)
class LurkerConfig:
    LURKER_LOG_LEVEL: Union[int, str] = "INFO"
    """The log level of the lurker application according to the python logging module."""
    LURKER_LOG_FILE: Optional[str] = "lurkerlog"
    """If specified, lurker additionally logs a file with the given name in the current working directory."""
    LURKER_INPUT_DEVICE: Optional[str] = None
    """Name of the device that should be used for recording audio. This might also be a substring of the actual name."""
    LURKER_OUTPUT_DEVICE: Optional[str] = None
    """Name of the device that should be used for playing feedback sounds. This might also be a substring of the actual name."""
    LURKER_KEYWORD: str = "hey john"
    """A word sequence upon which lurker should start recording actions."""
    LURKER_MODEL: str = "tiny"
    """A model name or an absolute path to a model file that should be used by the transcription engine."""
    LURKER_LANGUAGE: str = "en"
    """The language of the spoken words that should be transcribed by lurker. Setting this value usually improves transcription time."""
    LURKER_SPEECH_CONFIG: SpeechConfig = field(default_factory=SpeechConfig)
    """Configuration of audio queues and how to determine if a queue should be handed over to the more expensive transcription process."""
    LURKER_HANDLER_MODULE: str = "src.handlers.hue_client"
    """Module name containing a single implementation of src.action.ActionHandler to be used for acting on recorded instructions."""
    LURKER_HANDLER_CONFIG: Dict[str, str] = field(default_factory=dict)
    """Configuration passed to the configured ActionHandler."""
    LURKER_ACTION_REFRESH_INTERVAL: Union[int, str] = 5
    """Duration in seconds between action reloading attempts."""

    def to_pretty_str(self) -> str:
        key_value_strings = [f"{field_name}={value}" for field_name, value in dataclasses.asdict(self).items()]
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

    if LURKER_HANDLER_CONFIG in config_param_dict:
        handler_config_param_value = config_param_dict[LURKER_HANDLER_CONFIG]
        if type(handler_config_param_value) is not dict:
            # transform param value to a string and try to load it as a dictionary
            handler_config_param_value = json.loads(str(handler_config_param_value))
            config_param_dict[LURKER_HANDLER_CONFIG] = handler_config_param_value

    return LurkerConfig(**config_param_dict)