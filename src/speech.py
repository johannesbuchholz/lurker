import time
from collections import deque
from threading import Thread
from time import sleep
from typing import Callable, Any

import numpy as np
import sounddevice as sd
import whisper

from src import log, utils

LOGGER = log.new_logger("Lurker ({})".format(__name__))


def fill_queue_callback(queue: deque) -> Callable[[np.array, int, Any, sd.CallbackFlags], None]:
    return lambda indata, frames, t, status: queue.extend(indata[:, 0])


class SpeechToTextListener:

    def __init__(self,
                 sample_rate: int = 16_000,
                 bit_depth: np.dtype = np.dtype(np.int16),
                 instruction_callback: Callable[[str], bool] = lambda s: False
                 ):
        self.model: whisper.Whisper = whisper.load_model("tiny")
        self.decoding_options = {"language": "de", "suppress_blank": False, "fp16": False}

        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.callback = instruction_callback

        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(1.2 * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(3 * byte_count_per_second))
        self.is_listening = False

    def start_listening(self, key_word: str) -> None:
        if self.is_listening:
            return
        LOGGER.info("Start recording using keyword '%s'", key_word)
        Thread(target=self._start_listen_loop, name="lurker-listen-loop", args=[key_word], daemon=True).start()

    def stop_listening(self):
        self.is_listening = False

    def _start_listen_loop(self, key_word: str):
        self.is_listening = True
        while self.is_listening:
            if self._wait_for_keyword(key_word):
                utils.play_blib()
                instruction = self._record_instruction(timeout_ms=5000)
                LOGGER.info("Extracted instruction: %s", instruction)
                self._clear_queues()

                if self.callback(instruction):
                    LOGGER.info("Successfully acted on instruction: {}".format(instruction))
                else:
                    LOGGER.info("Could not act on instruction: {}".format(instruction))
                    utils.play_no()

    def _start_new_audio_stream(self,
                                callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> sd.InputStream:
        return sd.InputStream(device=None,
                              channels=1, dtype=self.bit_depth.str, callback=callback, samplerate=self.sample_rate)

    def _wait_for_keyword(self, key_word: str) -> bool:
        with self._start_new_audio_stream(fill_queue_callback(queue=self.keyword_queue)):
            intermediate_decode = ""
            while self.is_listening and key_word not in intermediate_decode:
                LOGGER.debug("Did not find keyword '%s' in '%s'", key_word, intermediate_decode)
                intermediate_decode = self._transcribe(self.keyword_queue)
                sleep(0.2)
            if key_word in intermediate_decode:
                LOGGER.info("Found keyword '%s' in '%s'", key_word, intermediate_decode)
                return True
            return False

    def _record_instruction(self, timeout_ms: int) -> str:
        with (self._start_new_audio_stream(fill_queue_callback(queue=self.instruction_queue))):
            start = time.time_ns()
            # TODO: Maybe replace waiting for full queue by a more dynamic approach like waiting fo a longer pause.
            LOGGER.debug("Waiting for action queue to be filled: queue_length={}, timeout_ms={}"
                         .format(self.instruction_queue.maxlen, timeout_ms))
            while self.is_listening and (len(self.instruction_queue) < self.instruction_queue.maxlen and
                                         time.time_ns() < start + timeout_ms * (10**6)):
                sleep(0.2)
            recorded_instruction: str = self._transcribe(self.instruction_queue)
            LOGGER.debug("Recorded instruction: sample_count={}, text={}".format(len(self.instruction_queue), recorded_instruction))
            return recorded_instruction

    def _clear_queues(self) -> None:
        self.keyword_queue.clear()
        self.instruction_queue.clear()

    def _transcribe(self, data) -> str:
        """
        Taken from https://github.com/davabase/whisper_real_time/blob/master/transcribe_demo.py
        """
        # load audio and pad/trim it to fit 30 seconds. There it says:
        #   Convert in-ram buffer to something the model can use directly without needing a temp file.
        #   Convert data from 16 bit wide integers to floating point with a width of 32 bits.
        #   Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
        audio = np.array(data, dtype=self.bit_depth).astype(np.float32) / 32768.
        audio = whisper.pad_or_trim(audio)

        # decode the audio
        result = self.model.transcribe(audio,
                                       no_speech_threshold=0.4,
                                       condition_on_previous_text=False,
                                       without_timestamps=True,
                                       language="de",
                                       suppress_blank=True,
                                       fp16=False)
        return result["text"].strip().lower()
