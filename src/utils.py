import os
from getpass import getuser
from pathlib import Path
from threading import Thread
from typing import Callable, Any


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
    return p


def _execute_command_in_background(command: str) -> None:
    Thread(target=lambda: os.system("{} 1>/dev/null 2>/dev/null".format(command)), daemon=True).start()


def _get_env(env_name: str, default: str, mapper: Callable[[str], Any] = lambda x: x) -> Any:
    env_value = os.environ.get(env_name, default)
    return mapper(env_value)


class Constants:
    LURKER_LOG_LEVEL: str = _get_env(
        "LURKER_LOG_LEVEL", "DEBUG")

    LURKER_ENABLE_DYNAMIC_CONFIGURATION: bool = _get_env(
        "LURKER_ENABLE_DYNAMIC_CONFIGURATION", "False", lambda x: str(x).lower == "true")

    _media_path = "/media/" + getuser()
    _default_home_path = None
    if LURKER_ENABLE_DYNAMIC_CONFIGURATION and Path(_media_path).exists():
        _first_media_path = next(os.scandir(_media_path), None)
        _default_home_path = str(_first_media_path.path) + "/lurker" if _first_media_path is not None else None
    if _default_home_path is None:
        _default_home_path = str(Path().home()) + "/lurker"

    LURKER_HOME: str = _get_env(
        "LURKER_HOME", _default_home_path)

    LURKER_KEYWORD: str = _get_env(
        "LURKER_KEYWORD", "")

    LURKER_SOUND_TOOL: str = _get_env(
        "LURKER_SOUND_TOOL", "/usr/bin/aplay")

    KEYWORD_QUEUE_LENGTH_SECONDS: float = _get_env(
        "LURKER_KEYWORD_QUEUE_LENGTH_SECONDS", "0.8", lambda x: float(x))

    INSTRUCTION_QUEUE_LENGTH_SECONDS: float = _get_env(
        "INSTRUCTION_QUEUE_LENGTH_SECONDS", "3", lambda x: float(x))
