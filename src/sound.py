import os
import wave
from typing import Dict, Optional

import numpy as np
import sounddevice as sd

from src import log

LOGGER = log.new_logger(__name__)


def play_ready(output_device_name: Optional[str]) -> None:
    entry = _LoadedSounds.sounds.get("ready.wav", None)
    _play_sound(output_device_name, entry)


def play_startup(output_device_name: Optional[str]):
    entry = _LoadedSounds.sounds.get("start.wav", None)
    _play_sound(output_device_name, entry)


def play_no(output_device_name: Optional[str]):
    entry = _LoadedSounds.sounds.get("no.wav", None)
    _play_sound(output_device_name, entry)


def play_ok(output_device_name: Optional[str]):
    entry = _LoadedSounds.sounds.get("ok.wav", None)
    _play_sound(output_device_name, entry)


def play_understood(output_device_name: Optional[str]):
    entry = _LoadedSounds.sounds.get("understood.wav", None)
    _play_sound(output_device_name, entry)


def _play_sound(output_device_name: Optional[str], data: Optional[np.ndarray]) -> None:
    if data is not None:
        try:
            sd.play(data, device=output_device_name)
        except Exception as e:
            LOGGER.warning(f"Could not play sound: {str(e)}")


def load_sounds():
    LOGGER.info("Loading sounds")
    sounds = {}
    resources_dir = os.scandir(os.path.dirname(__file__) + "/resources")
    for p in resources_dir:
        if p.name.endswith(".wav"):
            try:
                with wave.open(p.path, "rb") as f:
                    buffer = f.readframes(f.getnframes())
                    # Convert the buffer to a numpy array by checking the size of the sample
                    # width in bytes. The output will be a 1D array with interleaved channels.
                    interleaved = np.frombuffer(buffer, dtype=f'int{f.getsampwidth() * 8}')
                    # Reshape it into a 2D array separating the channels in columns.
                    data = np.reshape(interleaved, (-1, f.getnchannels()))
                    sounds[p.name] = data
            except Exception as e:
                LOGGER.warning("Could not load sound from %s: %s", p.path, str(e))
    LOGGER.debug(f"Loaded sounds: size={len(sounds)}, files={sounds.keys()}")
    _LoadedSounds.sounds = sounds


class _LoadedSounds:
    sounds: Dict[str, np.ndarray] = {}
