from __future__ import annotations

import json
import queue
import threading
from collections import deque
from typing import Callable, List, TYPE_CHECKING

from vosk import Model, KaldiRecognizer

from src import log

if TYPE_CHECKING:
    from src.lurker import Keyword


class Transcriber:

    def __init__(self, callback: Callable[[str], None], keyword: Keyword, model_path: str, sample_rate: int = 16000, max_words: int = 200):
        self._logger = log.new_logger(self.__class__.__name__)

        self._model = Model(model_path)
        self._recognizer = KaldiRecognizer(self._model, sample_rate)
        self._recognizer.SetWords(True)

        self._transcription: deque[str] = deque(maxlen=max_words)
        self._callback = callback
        self._keyword = keyword

        self._keyword_candidate_queue: queue.Queue[List[str]] = queue.Queue(maxsize=3)
        self._keyword_candidate_worker = threading.Thread(target=self._check_fo_keyword, daemon=True)
        self._keyword_candidate_worker.start()


    def _check_fo_keyword(self) -> None:
        """
        Inspects candidates for key word and sends to callback if necessary.
        1. Polls the next candidate if available, else waits
        2. Checks if the keyword is present in the current candidate.
        3. Submits the concatenated Strings after the keyword to the callback.
        """
        pass

    def feed_data(self, pcm_bytes: bytes) -> None:
        if self._recognizer.AcceptWaveform(pcm_bytes):
            result_str = self._recognizer.Result()
            try:
                result = json.loads(result_str)
            except Exception as e:
                self._logger.warning(f"Could not read ASR result: {result_str} ({e})", exc_info=True)
                return

            text = result.get("text", "").strip()
            if text:
                self._push_text(text)

    def reset(self) -> None:
        self._recognizer.Reset()
        self._transcription.clear()

    def _push_text(self, text: str) -> None:
        incoming = text.split()
        if len(incoming) == 0:
            return
        self._transcription.extend(incoming)
        try:
            self._keyword_candidate_queue.put_nowait(incoming)
        except queue.Full:
            self._logger.warning(f"Transcription queue is full: dropping={incoming}")
            pass

    def get_text(self) -> str:
        return " ".join(self._transcription)

    def shutdown(self) -> None:
        self._keyword_candidate_queue.put(None)
        self._keyword_candidate_worker.join(timeout=5)
