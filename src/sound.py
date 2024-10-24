import os
import wave
from typing import Dict, Tuple, Optional

import numpy as np
import sounddevice as sd

from src import log

LOGGER = log.new_logger(__name__)


def play_ready(output_device_name: Optional[str]) -> None:
    entry = _LoadedSounds.sounds.get("ready.wav", ())
    _play_sound(output_device_name, entry)


def play_positive(output_device_name: Optional[str]) -> None:
    entry = _LoadedSounds.sounds.get("positive.wav", ())
    _play_sound(output_device_name, entry)


def play_negative(output_device_name: Optional[str]):
    entry = _LoadedSounds.sounds.get("negative.wav", ())
    _play_sound(output_device_name, entry)


def _play_sound(output_device_name: Optional[str], data_and_samplerate: Tuple[np.ndarray, int]) -> None:
    if data_and_samplerate:
        try:
            data, samplerate = data_and_samplerate
            sd.play(data, device=output_device_name, samplerate=samplerate)
        except Exception as e:
            LOGGER.warning(f"Could not play: {str(e)}")


def load_sounds():
    LOGGER.info("Loading sounds")
    sounds = {}
    resources_dir = os.scandir(os.path.dirname(__file__) + "/resources")
    for p in resources_dir:
        if p.name.endswith(".wav"):
            try:
                with wave.open(p.path, "rb") as f:
                    # Read the whole file into a buffer. If you are dealing with a large file
                    # then you should read it in blocks and process them separately.
                    buffer = f.readframes(f.getnframes())
                    # Convert the buffer to a numpy array by checking the size of the sample
                    # width in bytes. The output will be a 1D array with interleaved channels.
                    interleaved = np.frombuffer(buffer, dtype=f'int{f.getsampwidth() * 8}')
                    # Reshape it into a 2D array separating the channels in columns.
                    data = np.reshape(interleaved, (-1, f.getnchannels()))
                    sounds[p.name] = (data, f.getframerate())
            except Exception as e:
                LOGGER.warning("Could not load sound from %s: %s", p.path, str(e))
    _LoadedSounds.sounds = sounds


class _LoadedSounds:
    sounds: Dict[str, Tuple[np.ndarray, int]] = {}
