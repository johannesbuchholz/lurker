import numpy as np
import whisper


class Transcriber:
    """
    Abstraction of actual transcription engine in use.
    """

    def __init__(self, model_path: str):
        self.model: whisper.Whisper = whisper.load_model(model_path, in_memory=True)
        self.sample_rate = 16_000
        self.bit_depth = np.dtype(np.int16)

    # TODO: Maybe explore more CPU-friendly alternatives like https://github.com/ggerganov/whisper.cpp
    def transcribe(self, data) -> str:
        """
        Taken from https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
        """
        # load audio and pad/trim it to fit 30 seconds. There it says:
        #   Convert in-ram buffer to something the model can use directly without needing a temp file.
        #   Convert data from 16 bit wide integers to floating point with a width of 32 bits.
        #   Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
        audio = np.array(data, dtype=self.bit_depth).astype(np.float32) / 32768.
        result = self.model.transcribe(audio,
                                       condition_on_previous_text=False,
                                       prepend_punctuations="",
                                       append_punctuations="",
                                       without_timestamps=True,
                                       fp16=False,
                                       language="de"
                                       )
        return result["text"].strip().lower()