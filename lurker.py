import time
from collections import deque
from time import sleep
from typing import Optional, Callable, Any

import numpy as np
import sounddevice as sd
from deepspeech import Model

from log import logger
from utils import BackgroundExitCondition

HOT_WORDS_AND_BOOST = [("hey", 8.5), ("listen", 8), ("now", 4)]


def fill_queue_callback(queue: deque) -> Callable[[np.array, int, Any, sd.CallbackFlags], None]:
    return lambda indata, frames, t, status: queue.extend(indata[:, 0])


class SpeechToTextListener:

    def __init__(self,
                 model_path: str,
                 scorer_path: Optional[str] = None,
                 sample_rate: int = 16_000,
                 bit_depth: np.dtype = np.dtype(np.int16)
                 ):
        self.exit_condition = BackgroundExitCondition()
        self.model = Model(model_path)
        if scorer_path:
            self.model.enableExternalScorer(scorer_path)
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(0.8 * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(3 * byte_count_per_second))

    def begin_recording(self, key_word: str) -> None:
        logger.info("Start recording using keyword '%s'", key_word)
        for word, boost in HOT_WORDS_AND_BOOST:
            self.model.addHotWord(word, boost)

        self.exit_condition.start_evaluating_in_background()
        while not self.exit_condition.is_met():
            self._wait_for_keyword(key_word)
            words = self._get_instruction_words(timeout_ms=3000)
            logger.info("Received instruction words: %s", words)
            self._clear_queues()
        logger.info("Closing SpeechToTextListener")

    def _start_new_audio_stream(self,
                                callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> sd.InputStream:
        return sd.InputStream(device=None,
                              channels=1, dtype=self.bit_depth.str, callback=callback, samplerate=self.sample_rate)

    def _wait_for_keyword(self, key_word: str) -> None:
        with self._start_new_audio_stream(fill_queue_callback(queue=self.keyword_queue)):
            intermediate_decode = ""
            while (not self.exit_condition.is_met() and
                   key_word not in intermediate_decode):
                logger.debug("Did not find keyword '%s' in '%s'", key_word, intermediate_decode)
                intermediate_decode = self.model.stt(np.array(self.keyword_queue, dtype=self.bit_depth))
                sleep(0.2)
            logger.info("Found keyword '%s' in '%s'", key_word, intermediate_decode)
            return

    def _get_instruction_words(self, timeout_ms: int) -> str:
        with (self._start_new_audio_stream(fill_queue_callback(queue=self.instruction_queue))):
            start = time.time_ns()
            while (not self.exit_condition.is_met() and
                   len(self.instruction_queue) < self.instruction_queue.maxlen and
                   time.time_ns() < start + timeout_ms * 10**8):
                logger.debug("Waiting for instruction queue to be filled: %s", int(len(self.instruction_queue) / self.instruction_queue.maxlen * 100))
                time.sleep(0.2)
            return self.model.stt(np.array(self.instruction_queue, dtype=np.int16))

    def _clear_queues(self) -> None:
        self.keyword_queue.clear()
        self.instruction_queue.clear()


(SpeechToTextListener("deepspeech-0.9.3-models.pbmm","deepspeech-0.9.3-models.scorer")
 .begin_recording(key_word="hey jenny"))
