import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Any

from src import log

LURKER_KEYWORD = "LURKER_KEYWORD"
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


def _get_envs() -> dict[str, str]:
    envs = {
        LURKER_LOG_LEVEL: os.environ.get(LURKER_LOG_LEVEL),
        LURKER_LOG_FILE: os.environ.get(LURKER_LOG_FILE),
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


def _load_config_file(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        with open(path) as cfg_file_handle:
            cfg: dict = json.load(cfg_file_handle)
    else:
        LOGGER.info(f"No configuration file found at {path}")
        cfg = {}
    return cfg


@dataclass(frozen=True)
class SpeechDetectorConfig:
    sample_rate: int = 16000
    """Sample rate for WebRTC VAD. Valid values: 8000, 16000, 32000, 48000."""
    vad_aggressiveness: int = 3
    """WebRTC VAD aggressiveness (0-3), higher means more filtering."""
    energy_factor: float = 2.0
    """Multiplier above ambient noise level required to consider a chunk as speech."""
    energy_alpha_attack: float = 0.2
    """EMA smoothing factor when energy rises above ambient (fast attack). Higher = adapts faster to loud sounds."""
    energy_alpha_decay: float = 0.005
    """EMA smoothing factor when energy falls below ambient (slow decay). Lower = ambient stays high longer."""

    def __post_init__(self):
        valid_rates = [8000, 16000, 32000, 48000]
        if self.sample_rate not in valid_rates:
            LOGGER.warning(
                f"Sample rate {self.sample_rate} not optimal for WebRTC VAD. Valid rates: {valid_rates}"
            )


@dataclass(frozen=True)
class SpeechConfig:
    required_trailing_silence_chunks: int = 64
    """Number of trailing silent chunks required to consider speech ended in order to stop audio streaming to ASR backend. Set to negative if you want to only use full results as decided by the ASR-Backend."""
    prefill_chunks: int = 32
    """Number of pre-speech audio chunks buffered while gate is DOWN, pushed to ASR when gate opens for context."""
    frame_ms: int = 20
    max_open_gate_seconds: float = 4.0
    """Maximum time the gate stays open before force-flushing, in seconds."""
    detector: SpeechDetectorConfig = field(default_factory=SpeechDetectorConfig)
    """Configuration for speech detection (VAD + energy pre-filter)."""
    frame_samples: int = int(16000 * (20 / 1000))


@dataclass(frozen=True)
class LurkerConfig:
    LURKER_LOG_LEVEL: int | str = "INFO"
    """The log level of the lurker application according to the python logging module."""
    LURKER_LOG_FILE: str | None = "lurkerlog"
    """If specified, lurker additionally logs a file with the given name in the current working directory."""
    LURKER_INPUT_DEVICE: str | None = None
    """Name of the device that should be used for recording audio. This might also be a substring of the actual name."""
    LURKER_OUTPUT_DEVICE: str | None = None
    """Name of the device that should be used for playing feedback sounds. This might also be a substring of the actual name."""
    LURKER_KEYWORD: list[str] = field(default_factory=lambda : ["hey john"])
    """A word sequence upon which lurker should start recording actions."""
    LURKER_LANGUAGE: str = "en"
    """The language of the spoken words that should be transcribed by lurker. Setting this value usually improves transcription time."""
    LURKER_SPEECH_CONFIG: SpeechConfig = field(default_factory=SpeechConfig)
    """Configuration of audio queues and how to determine if a queue should be handed over to the more expensive transcription process."""
    LURKER_HANDLER_MODULE: str = "src.handlers.hue_client"
    """Module name containing a single implementation of src.action.ActionHandler to be used for acting on recorded instructions."""
    LURKER_HANDLER_CONFIG: dict[str, str] = field(default_factory=dict)
    """Configuration passed to the configured ActionHandler."""
    LURKER_ACTION_REFRESH_INTERVAL: int | str = 30
    """Duration in seconds between action reloading attempts."""

    def to_pretty_str(self) -> str:
        key_value_strings = [f"{field_name}={value}" for field_name, value in dataclasses.asdict(self).items()]
        return "\n".join(key_value_strings)


def load_lurker_config(config_path: str) -> LurkerConfig:
    config_param_dict: dict = _load_config_file(config_path) | _get_envs()
    if LURKER_KEYWORD in config_param_dict:
        # keyword_param_value may be str, a list from _load_config_file or a string representing a list from _get_envs
        keyword_param_value = config_param_dict[LURKER_KEYWORD]
        if type(keyword_param_value) is str:
            keyword_param_parsed = transform_to_list(keyword_param_value)
            if type(keyword_param_parsed) is not list:
                config_param_dict[LURKER_KEYWORD] = [keyword_param_parsed]
            else:
                config_param_dict[LURKER_KEYWORD] = keyword_param_parsed

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


def transform_to_list(original: str) -> list[str]:
    if original.startswith("[") and original.endswith("]"):
        return [item.replace("\"", "").replace("'", "").strip() for item in original[1:-1].split(",")]
    else:
        return [original]