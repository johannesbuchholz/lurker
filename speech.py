import time
from collections import deque
from threading import Thread
from time import sleep
from typing import Optional, Callable, Any

import numpy as np
import sounddevice as sd
from deepspeech import Model

from log import logger

HOT_WORDS_AND_BOOST = [("hey", 8), ("listen", 8), ("now", 4)]


def fill_queue_callback(queue: deque) -> Callable[[np.array, int, Any, sd.CallbackFlags], None]:
    return lambda indata, frames, t, status: queue.extend(indata[:, 0])


class SpeechToTextListener:

    def __init__(self,
                 model_path: str,
                 scorer_path: Optional[str] = None,
                 sample_rate: int = 16_000,
                 bit_depth: np.dtype = np.dtype(np.int16),
                 instruction_callback: Callable[[str], None] = lambda s: None
                 ):
        self.model = Model(model_path)
        if scorer_path:
            self.model.enableExternalScorer(scorer_path)
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.callback = instruction_callback

        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(0.8 * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(3 * byte_count_per_second))
        self.is_listening = False

    def start_recording_in_background(self, key_word: str) -> None:
        if self.is_listening:
            return
        logger.info("Start recording using keyword '%s'", key_word)
        for word, boost in HOT_WORDS_AND_BOOST:
            self.model.addHotWord(word, boost)
        Thread(target=self._start_listen_loop, name="lurker-listen-loop", args=[key_word], daemon=True).start()

    def stop_listening(self):
        self.is_listening = False

    def _start_listen_loop(self, key_word: str):
        self.is_listening = True
        while self.is_listening:
            self._wait_for_keyword(key_word)
            instruction = self._record_instruction(timeout_ms=3000)
            logger.info("Extracted instruction: %s", instruction)
            self._clear_queues()
            self.callback(instruction)

    def _start_new_audio_stream(self,
                                callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> sd.InputStream:
        return sd.InputStream(device=None,
                              channels=1, dtype=self.bit_depth.str, callback=callback, samplerate=self.sample_rate)

    def _wait_for_keyword(self, key_word: str) -> None:
        with self._start_new_audio_stream(fill_queue_callback(queue=self.keyword_queue)):
            intermediate_decode = ""
            while self.is_listening and key_word not in intermediate_decode:
                logger.debug("Did not find keyword '%s' in '%s'", key_word, intermediate_decode)
                intermediate_decode = self.model.stt(np.array(self.keyword_queue, dtype=self.bit_depth))
                sleep(0.2)
            logger.info("Found keyword '%s' in '%s'", key_word, intermediate_decode)
            return

    def _record_instruction(self, timeout_ms: int) -> str:
        with (self._start_new_audio_stream(fill_queue_callback(queue=self.instruction_queue))):
            start = time.time_ns()
            # TODO: Maybe replace waiting for full queue by a more dynamic approach like waiting fo a longer pause.
            while self.is_listening and (len(self.instruction_queue) < self.instruction_queue.maxlen and
                                         time.time_ns() < start + timeout_ms * 10 ** 8):
                logger.debug("Waiting for action queue to be filled: %s",
                             int(len(self.instruction_queue) / self.instruction_queue.maxlen * 100))
                time.sleep(0.2)
            return self.model.stt(np.array(self.instruction_queue, dtype=np.int16))

    def _clear_queues(self) -> None:
        self.keyword_queue.clear()
        self.instruction_queue.clear()
