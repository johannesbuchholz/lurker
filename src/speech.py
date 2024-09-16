from collections import deque
from time import sleep
from typing import Callable, Any, Optional

import numpy as np
import sounddevice as sd

from src import log, sound
from src.text import filter_non_alnum
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)


class SpeechToTextListener:
    def __init__(self,
                 transcriber: Transcriber,
                 keyword_queue_length_seconds: float,
                 instruction_queue_length_seconds: float,
                 silence_threshold: int,
                 input_device_name: Optional[str],
                 output_device_name: Optional[str],
                 instruction_callback: Callable[[str], bool] = lambda x: {},
                 ):
        """
        :param instruction_callback: A callable acting on some instruction string. Returns a boolean to indicate if
        acting on the instruction has been successful.
        """
        self.transcriber = transcriber
        self.sample_rate = 16_000
        self.bit_depth = np.dtype(np.int16)

        self.callback = instruction_callback
        self.silence_threshold = silence_threshold
        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(keyword_queue_length_seconds * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(instruction_queue_length_seconds * byte_count_per_second))
        self.is_listening = False

    def start_listening(self, keyword: str, lurker_keyword_interval_seconds: float):
        if keyword is None:
            raise ValueError("Keyword can not be None")
        if self.is_listening:
            LOGGER.debug("Already listening.")
            return
        LOGGER.info("Start recording using keyword '%s'", keyword)
        self._start_listen_loop(keyword, lurker_keyword_interval_seconds)

    def stop_listening(self):
        self.is_listening = False

    def _start_listen_loop(self, keyword: str, lurker_keyword_interval_seconds: float):
        self.is_listening = True
        while self.is_listening:
            if self._wait_for_keyword(keyword, lurker_keyword_interval_seconds):
                sound.play_ready(self.output_device_name)
                instruction = self._record_instruction()
                LOGGER.info("Extracted instruction: %s", instruction)
                self._clear_queues()

                if self.callback(instruction):
                    LOGGER.info("Successfully acted on instruction: %s", instruction)
                    sound.play_positive(self.output_device_name)
                else:
                    LOGGER.info("Could not act on instruction: %s", instruction)
                    sound.play_negative(self.output_device_name)

    def _start_new_audio_stream(self,
                                callback: Callable[[np.ndarray, int, Any, sd.CallbackFlags], None]) -> sd.InputStream:
        try:
            return sd.InputStream(device=self.input_device_name,
                                  channels=1, dtype=self.bit_depth.str, callback=callback, samplerate=self.sample_rate)
        except ValueError as e:
            raise IOError("Could not create input stream", e)

    def _fill_keyword_queue(self, indata: np.ndarray, frames: int, t: Any, status: sd.CallbackFlags) -> None:
        return self.keyword_queue.extend(indata[:, 0])

    def _fill_instruction_queue(self, indata: np.ndarray, frames: int, t: Any, status: sd.CallbackFlags) -> None:
        return self.instruction_queue.extend(indata[:, 0])

    def _wait_for_keyword(self, keyword: str, lurker_keyword_interval_seconds: float) -> bool:
        with self._start_new_audio_stream(self._fill_keyword_queue):
            intermediate_decode: str = ""
            while self.is_listening and (intermediate_decode == "" or keyword not in intermediate_decode):
                LOGGER.debug("Did not find keyword '%s' in '%s'", keyword, intermediate_decode)
                if self._is_keyword_queue_relevant():
                    transcription = self.transcriber.transcribe(self.keyword_queue)
                    intermediate_decode = filter_non_alnum(transcription)
                else:
                    intermediate_decode = ""
                sleep(lurker_keyword_interval_seconds)
            if keyword in intermediate_decode:
                LOGGER.info("Found keyword '%s' in '%s'", keyword, intermediate_decode)
                return True
            return False

    def _record_instruction(self) -> str:
        with ((self._start_new_audio_stream(self._fill_instruction_queue))):
            LOGGER.debug("Waiting for action queue to be filled: queue_length_byte={}"
                         .format(self.instruction_queue.maxlen))
            while (self.is_listening
                   and not self._has_instruction_queue_speech_followed_by_silence()
                   and (len(self.instruction_queue) < self.instruction_queue.maxlen)):
                sleep(0.1)
            recorded_instruction: str = self.transcriber.transcribe(self.instruction_queue)
            LOGGER.debug("Recorded instruction: sample_count={}, text={}"
                         .format(len(self.instruction_queue), recorded_instruction))
            return recorded_instruction

    def _clear_queues(self) -> None:
        self.keyword_queue.clear()
        self.instruction_queue.clear()

    def _is_keyword_queue_relevant(self, bucket_count: int = 100, required_bucket_ratio: float = 0.1) -> bool:
        """
        Relevant means that at least in an appropriate amount of buckets the average absolute amplitude is above the
        threshold.

        threshold: 50
        means:
            12          77          155          11        18         55         51          19
        |##########|##########|##########|##########|##########|##########|##########|##########|          |          |
        0          1          2          3          4          5          6          7          8          9
                   |---above--|---above--|                     |---above--|---above--|
        """
        length = len(self.keyword_queue)
        max_length = self.keyword_queue.maxlen
        if length < max_length / 3:
            return False

        arr = np.array(self.keyword_queue)
        interval_length = int(max_length / bucket_count)
        threshold_breaking_buckets = 0
        for i in range(bucket_count):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = np.abs(arr[lower: upper]).mean()
            if bucket_mean > self.silence_threshold:
                threshold_breaking_buckets += 1
        return threshold_breaking_buckets > bucket_count * required_bucket_ratio

    def _has_instruction_queue_speech_followed_by_silence(self,
                                                          bucket_count: int = 100,
                                                          required_buckets_with_speech_ratio: float = 0.05,
                                                          required_silent_bucket_ratio: float = 0.2) -> bool:
        """
        The instruction is deemed to be spoken if some sound has been recorded followed by enough silence.

        threshold: 60
        means:
            12         25         78         77         65         51          13        32         28
        |##########|##########|##########|##########|##########|##########|##########|##########|##########|          |
        0          1          2          3          4          5          6          7          8          9
                              |---------over threshold---------|--------------under threshold -------------|
        """
        length = len(self.instruction_queue)
        max_length = self.instruction_queue.maxlen
        if length < max_length / 3:
            return False

        required_silent_buckets = bucket_count * required_silent_bucket_ratio
        required_buckets_with_speech = bucket_count * required_buckets_with_speech_ratio
        arr = np.array(self.instruction_queue)
        interval_length = int(max_length / bucket_count)
        last_bucket_with_speech = -1
        buckets_with_speech = 0
        last_silent_bucket = 0
        for i in range(bucket_count):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = np.abs(arr[lower: upper]).mean()
            if bucket_mean > self.silence_threshold:
                last_bucket_with_speech = i
                buckets_with_speech += 1
            else:
                last_silent_bucket = i
            if last_bucket_with_speech > 0 and buckets_with_speech > required_buckets_with_speech:
                # length may be negative
                silence_length = last_silent_bucket - last_bucket_with_speech
                if silence_length > required_silent_buckets:
                    LOGGER.debug("Instruction queue is ready")
                    return True
        return False
