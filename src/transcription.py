import logging

import numpy as np
from pywhispercpp.model import Model

PARAMS = {
    "translate": False,
    "no_context": True,
    "print_progress": False,
    "language": "de",
    "suppress_non_speech_tokens": True,
    "no_speech_thold": 0.4 # probably not implemented in whispercpp
}

class Transcriber:
    """
    Abstraction of actual transcription engine in use.
    """

    def __init__(self, model_path: str):
        # inputs = _get_whispercpp_model_inputs(model_path)
        self.model: Model = Model(model=model_path, log_level=logging.WARN, **PARAMS)

        self.sample_rate = 16_000
        self.bit_depth = np.dtype(np.int16)

    def transcribe(self, data) -> str:
        """
        Taken from https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
        """
        # load audio and pad/trim it to fit 30 seconds. There it says:
        #   Convert in-ram buffer to something the model can use directly without needing a temp file.
        #   Convert data from 16 bit wide integers to floating point with a width of 32 bits.
        #   Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
        audio = np.array(data, dtype=self.bit_depth).astype(np.float32) / 32768.
        segments = self.model.transcribe(audio)
        return " ".join([s.text for s in segments]).strip().lower()
