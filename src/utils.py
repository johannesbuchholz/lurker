import os
from getpass import getuser
from pathlib import Path
from threading import Thread
from typing import Callable, Any

from src import log

LOGGER = log.new_logger("Lurker ({})".format(__name__))


def play_blib() -> None:
    sound_path = _get_abs_path("resources/blib-sound.wav")
    _execute_command_in_background("{} {}".format(Constants.LURKER_SOUND_TOOL, sound_path))


def play_no():
    sound_path = _get_abs_path("resources/no-sound.wav")
    _execute_command_in_background("{} {}".format(Constants.LURKER_SOUND_TOOL, sound_path))


def filter_non_alnum(snippet) -> str:
    return ''.join([c for c in snippet.lower().strip() if c.isalnum() or c.isspace()])


def _get_abs_path(relative_path_to_this: str) -> Path:
    p = Path(__file__).parent.joinpath(relative_path_to_this)
    LOGGER.log(level=1, msg="Resolved path {} to {}".format(relative_path_to_this, p))
    return p


def _execute_command_in_background(command: str) -> None:
    LOGGER.debug("Executing command: '{}'".format(command))
    Thread(target=lambda: os.system("{} 1>/dev/null 2>/dev/null".format(command)), daemon=True).start()


def _get_env(env_name: str, default: str, mapper: Callable[[str], Any] = lambda x: x) -> Any:
    env_value = os.environ.get(env_name, default)
    return mapper(env_value)


class Constants:
    LURKER_LOG_LEVEL: str = _get_env("LURKER_LOG_LEVEL", "DEBUG")
    LOGGER.info("LURKER_LOG_LEVEL: %s", LURKER_LOG_LEVEL)

    LURKER_ENABLE_DYNAMIC_CONFIGURATION: bool = _get_env(
        "LURKER_ENABLE_DYNAMIC_CONFIGURATION", "False", lambda x: str(x).lower == "true")
    LOGGER.info("LURKER_ENABLE_DYNAMIC_CONFIGURATION: %s", LURKER_ENABLE_DYNAMIC_CONFIGURATION)

    _media_path = "/media/" + getuser()
    _default_home_path = None
    if LURKER_ENABLE_DYNAMIC_CONFIGURATION and Path(_media_path).exists():
        _first_media_path = next(os.scandir(_media_path), None)
        _default_home_path = str(_first_media_path.path) + "/lurker" if _first_media_path is not None else None
    if _default_home_path is None:
        _default_home_path = str(Path().home()) + "/lurker"

    LURKER_HOME: str = _get_env(
        "LURKER_HOME", _default_home_path)
    LOGGER.info("LURKER_HOME: %s", LURKER_HOME)

    LURKER_KEYWORD: str = _get_env("LURKER_KEYWORD", "")
    LOGGER.info("LURKER_KEYWORD: %s", LURKER_KEYWORD)

    LURKER_SOUND_TOOL: str = _get_env(
        "LURKER_SOUND_TOOL", "/usr/bin/aplay")
    LOGGER.info("LURKER_SOUND_TOOL: %s", LURKER_SOUND_TOOL)

    KEYWORD_QUEUE_LENGTH_SECONDS: float = _get_env(
        "LURKER_KEYWORD_QUEUE_LENGTH_SECONDS", "0.8", lambda x: float(x))
    LOGGER.info("KEYWORD_QUEUE_LENGTH_SECONDS: %s", KEYWORD_QUEUE_LENGTH_SECONDS)

    INSTRUCTION_QUEUE_LENGTH_SECONDS: float = _get_env(
        "INSTRUCTION_QUEUE_LENGTH_SECONDS", "3", lambda x: float(x))
    LOGGER.info("INSTRUCTION_QUEUE_LENGTH_SECONDS: %s", INSTRUCTION_QUEUE_LENGTH_SECONDS)
