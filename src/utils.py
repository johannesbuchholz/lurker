import os
import wave

import numpy as np
import sounddevice as sd

from src import log, config
from src.config import CONFIG

LOGGER = log.new_logger("Lurker ({})".format(__name__), level=CONFIG.log_level())


def play_blib() -> None:
    sound_path = os.path.abspath("src/resources/blib-sound.wav")
    play_sound(sound_path)


def play_no():
    sound_path = os.path.abspath("src/resources/no-sound.wav")
    play_sound(sound_path)


def filter_non_alnum(snippet) -> str:
    return ''.join([c for c in snippet.lower().strip() if c.isalnum() or c.isspace()])


# TODO: Read sound data into memory instead of reading it from disk each time
def play_sound(file: str) -> None:
    try:
        with wave.open(file, "rb") as f:
            # Read the whole file into a buffer. If you are dealing with a large file
            # then you should read it in blocks and process them separately.
            buffer = f.readframes(f.getnframes())
            # Convert the buffer to a numpy array by checking the size of the sample
            # width in bytes. The output will be a 1D array with interleaved channels.
            interleaved = np.frombuffer(buffer, dtype=f'int{f.getsampwidth() * 8}')
            # Reshape it into a 2D array separating the channels in columns.
            data = np.reshape(interleaved, (-1, f.getnchannels()))
            sd.play(data, device=config.CONFIG.output_device(), samplerate=f.getframerate())
    except Exception as e:
        LOGGER.warning("Could not play sound from %s: %s", file, str(e))
