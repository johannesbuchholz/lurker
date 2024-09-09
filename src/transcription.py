import os.path
import re
from typing import Dict

import numpy as np
from whispercpp import Whisper


class Transcriber:
    """
    Abstraction of actual transcription engine in use.
    Params:
        strategy=WHISPER_SAMPLING_GREEDY
        greedy={best_of=1}
        language='de'
        num_threads=4
        num_max_text_ctx=16384
        offset_ms=0
        duration_ms=0
        translate=0
        no_context=1
        single_segment=0
        print_special=0
        print_progress=0
        print_realtime=0
        print_timestamps=0
        token_timestamps=0
        timestamp_token_probability_threshold=0.010000
        timestamp_token_sum_probability_threshold=0.010000
        max_segment_length=0
        split_on_word=1
        max_tokens=0
        speed_up=0
        audio_ctx=0
        prompt_tokens=0
        promp_num_tokens=0
        suppress_blank=1
        suppress_non_speech_tokens=1
        temperature=0.000000
        max_initial_timestamps=1.000000
        length_penalty=-1.000000
        temperature_inc=0.200000
        entropy_threshold=2.400000
        logprob_threshold=-1.000000
        no_speech_threshold=0.6
    """

    def __init__(self, model_path: str, language: str = "de"):
        inputs = _get_whispercpp_model_inputs(model_path)
        self.model: Whisper = Whisper.from_pretrained(**inputs)
        self.model.params.translate = False
        self.model.params.language = language
        self.model.params.print_timestamps = False
        self.model.params.print_special = False
        self.model.params.no_context = True
        self.model.params.suppress_blank = True
        self.model.params.suppress_non_speech_tokens = True
        self.model.params.audio_ctx = 0
        self.model.params.no_speech_threshold = 0.33

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
        return self.model.transcribe(audio).strip().lower()


def _get_whispercpp_model_inputs(model_path: str) -> Dict[str, str]:
    """
    The used whispercpp library can only take a model name like "tiny" or "base", not an absolute file name.
    It will only download that model unless a model with appropriate name is contained in "basedir".
    Hence, we split the model_path to simulate an already downloaded model.
    """
    if not os.path.isabs(model_path):
        # No special treatment. Assume model_path is something linke "tiny" or "base.en".
        return {"model_name": model_path}
    if not os.path.isfile(model_path):
        raise ValueError("Path to model must point to a file: " + model_path)
    # If here, we assume a model path like "/path/to/model/ggml-<modelname>.bin"
    regex = re.compile(r"ggml-(?P<name>.+)(\.bin)")
    basename = os.path.basename(model_path)
    match = regex.match(basename)
    if match:
        containing_dir_name = os.path.dirname(model_path)
        if os.path.basename(containing_dir_name) != "whispercpp":
            raise ValueError("The specified model must be contained in dir 'whispercpp' like '/a/b/c/whispercpp/ggml-<modelname>.bin': " + model_path)
        return {"model_name": match.group("name"), "basedir": os.path.dirname(containing_dir_name)}
    raise ValueError("Given model file name did not match the expected regular expression: name=%s, regex=%s"
                     .format(basename, regex))

