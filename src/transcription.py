import json
import threading
from collections import deque
from typing import Callable

from vosk import Model, KaldiRecognizer

from src import log
from src.keyword import Keyword


class Transcriber:

    def __init__(self, callback: Callable[[str], None], keyword: Keyword, model_path: str, sample_rate: int = 16000, max_words: int = 80):
        self._logger = log.new_logger(self.__class__.__name__)

        self._model = Model(model_path)
        self._recognizer = KaldiRecognizer(self._model, sample_rate)
        self._recognizer.SetWords(True)

        self._transcription: deque[str] = deque(maxlen=max_words)
        self._callback = callback
        self._keyword = keyword

    def feed_data(self, pcm_bytes: bytes) -> bool:
        return self._recognizer.AcceptWaveform(pcm_bytes)

    def check_for_keyword(self) -> None:
        """
        Checks accumulated transcription for keyword and fires callback if found.
        On keyword match, resets recognizer and clears transcription.
        """
        partial_str = self._recognizer.PartialResult()
        partial = {}
        try:
            partial = json.loads(partial_str)
        except Exception as e:
            self._logger.warning(f"Could not read partial result: {partial_str} ({e})", exc_info=True)
        partial_text = partial.get("partial", "").strip()
        if partial_text:
            self._transcription.extend(partial_text.split())

        full_text = self._get_text()
        keyword_end_index = self._keyword.is_in(full_text)
        instruction = ""
        has_keyword = keyword_end_index is not None
        if has_keyword:
            instruction = full_text[keyword_end_index:].strip()
            self._reset()
            if instruction:
                threading.Thread(name=instruction, target=self._callback, args=(instruction,), daemon=True).start()
        self._logger.debug(f"Flush (keyword={has_keyword}): full_text=\"{full_text}\", instruction=\"{instruction}\"")

    def _reset(self):
        self._recognizer.Reset()
        self._transcription.clear()

    def _get_text(self) -> str:
        return " ".join(self._transcription)
