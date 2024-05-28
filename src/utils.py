import os
from pathlib import Path
from threading import Thread

from src import log

SOUND_TOOL = "/usr/bin/aplay"  # alsa included tool

LOGGER = log.new_logger("Lurker ({})".format(__name__))


def get_abs_path(relative_path_to_this: str) -> str:
    p = str(Path(__file__).parent.joinpath(relative_path_to_this))
    LOGGER.log(level=1, msg="Resolved path {} to {}".format(relative_path_to_this, p))
    return p


def play_blib() -> None:
    sound_path = get_abs_path("resources/blib-sound.wav")
    _execute_command_in_background("{} {}".format(SOUND_TOOL, sound_path))


def play_no():
    sound_path = get_abs_path("resources/no-sound.wav")
    _execute_command_in_background("{} {}".format(SOUND_TOOL, sound_path))


def _execute_command_in_background(command: str) -> None:
    LOGGER.debug("Executing command: '{}'".format(command))
    Thread(target=lambda: os.system("{} 1>/dev/null 2>/dev/null".format(command)), daemon=True).start()


def filter_non_alnum(snippet) -> str:
    return ''.join([c for c in snippet.lower().strip() if c.isalnum() or c.isspace()])
