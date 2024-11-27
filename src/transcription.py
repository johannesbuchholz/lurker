import numpy as np
import whisper

class Transcriber:
    """
    Abstraction of actual transcription engine in use.
    """

    def __init__(self, model_path: str, spoken_language: str):
        self.model: whisper.Whisper = whisper.load_model(model_path, in_memory=True)
        self.spoken_language = spoken_language
        self.sample_rate = 16_000
        self.bit_depth = np.dtype(np.int16)

    def transcribe(self, data) -> str:
        """
        Taken from https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
        """
        #   Convert in-ram buffer to something the model can use directly without needing a temp file.
        #   Convert data from 16 bit wide integers to floating point with a width of 32 bits.
        #   Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
        audio = np.array(data, dtype=self.bit_depth).astype(np.float32) / 32768.
        result = self.model.transcribe(whisper.pad_or_trim(audio),
                                       condition_on_previous_text=False,
                                       without_timestamps=True,
                                       word_timestamps=False,
                                       fp16=False,
                                       language=self.spoken_language
                                       )
        return result["text"].strip().lower()