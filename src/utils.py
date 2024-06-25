import os
from pathlib import Path
from threading import Thread

from src.config import CONFIG


def play_blib() -> None:
    sound_path = _get_abs_path("resources/blib-sound.wav")
    _execute_command_in_background("{} {}".format(CONFIG.sound_tool(), sound_path))


def play_no():
    sound_path = _get_abs_path("resources/no-sound.wav")
    _execute_command_in_background("{} {}".format(CONFIG.sound_tool(), sound_path))


def filter_non_alnum(snippet) -> str:
    return ''.join([c for c in snippet.lower().strip() if c.isalnum() or c.isspace()])


def _get_abs_path(relative_path_to_this: str) -> Path:
    p = Path(__file__).parent.joinpath(relative_path_to_this)
    return p


def _execute_command_in_background(command: str) -> None:
    Thread(target=lambda: os.system("{} 1>/dev/null 2>/dev/null".format(command)), daemon=True).start()
