import re

import numpy as np
import sherpa_onnx
from sherpa_onnx import OnlineRecognizer

from src import log
from src.keyword import Keyword
from src.speech import ASRBackend, AudioChunk

_PUNCTUATION = re.compile(r"[^'\w\s%-]")


def _normalize(text: str) -> str:
    return " ".join(_PUNCTUATION.sub(" ", text).split()).lower()


def _pcm_to_float32(samples: np.ndarray) -> np.ndarray:
    if np.issubdtype(samples.dtype, np.signedinteger):
        info = np.iinfo(samples.dtype)
        return samples.astype(np.float32) / max(abs(info.min), info.max)

    if np.issubdtype(samples.dtype, np.floating):
        return samples.astype(np.float32)

    raise TypeError(f"Unsupported PCM dtype: {samples.dtype}")


class Transcriber(ASRBackend):

    def __init__(self, keyword: Keyword, model_dir_path: str, sample_rate: int = 16000):
        self._logger = log.new_logger(self.__class__.__name__)
        self._sample_rate = sample_rate
        self._recognizer: OnlineRecognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=f"{model_dir_path}/encoder.onnx",
            decoder=f"{model_dir_path}/decoder.onnx",
            joiner=f"{model_dir_path}/joiner.onnx",
            tokens=f"{model_dir_path}/tokens.txt",
            sample_rate=sample_rate,
            num_threads=2
        )
        self._keyword = keyword
        self._stream = self._recognizer.create_stream()

    def feed_data(self, chunk: AudioChunk) -> bool:
        samples = _pcm_to_float32(chunk.samples)
        self._stream.accept_waveform(chunk.sample_rate, samples)

        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        return self._recognizer.is_endpoint(self._stream)

    def check_for_keyword(self) -> str | None:
        """
        Checks accumulated transcription for keyword and fires callback if found.
        On keyword match, resets recognizer and clears transcription.
        """
        raw_result: str = self._recognizer.get_result(self._stream).strip()
        result: str = _normalize(raw_result)

        keyword_end_index = self._keyword.is_in(result)
        instruction = None
        has_keyword = keyword_end_index is not None
        if has_keyword:
            instruction = result[keyword_end_index:].strip()
            self._recognizer.reset(self._stream)
        elif len(result) > 160:
            # reset recognizer regardless of keyword match if it became too long
            self._recognizer.reset(self._stream)

        self._logger.debug(f"Checked: has_keyword={has_keyword}, "
                           f"raw=\"{raw_result}\", text=\"{result}\", instruction=\"{instruction}\"")
        return instruction
