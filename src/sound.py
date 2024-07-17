import os
import wave
from typing import Dict, Tuple

import numpy as np
import sounddevice as sd

from src import log, config
from src.config import CONFIG

LOGGER = log.new_logger("Lurker ({})".format(__name__), level=CONFIG.log_level())

def play_positive() -> None:
    entry = _SOUNDS.get("blib-sound.wav")
    if entry:
        _play_sound(*entry)


def play_negative():
    entry = _SOUNDS.get("no-sound.wav")
    if entry:
        _play_sound(*entry)


def _play_sound(sound_data: np.ndarray, samplerate: int) -> None:
    try:
        sd.play(sound_data, device=config.CONFIG.output_device(), samplerate=samplerate)
    except Exception as e:
        LOGGER.warning("Could not play : %s", str(e))


def _load_sounds() -> Dict[str, Tuple[np.ndarray, int]]:
    sounds = {}
    for p in os.scandir(os.path.abspath("src/resources")):
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
    return sounds


LOGGER.info("Loading sounds")
_SOUNDS = _load_sounds()
