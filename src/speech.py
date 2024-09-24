from collections import deque
from time import sleep
from typing import Callable, Any, Optional, Collection

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

    def _start_new_input_audio_stream(self,
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
        with self._start_new_input_audio_stream(self._fill_keyword_queue):
            intermediate_decode: str = ""
            while self.is_listening and (intermediate_decode == "" or keyword not in intermediate_decode):
                LOGGER.debug("Did not find keyword '%s' in '%s'", keyword, intermediate_decode)
                if self._is_keyword_queue_relevant():
                    LOGGER.debug("Keyword queue is relevant")
                    transcription = self.transcriber.transcribe(self.keyword_queue)
                    intermediate_decode = filter_non_alnum(transcription)
                else:
                    LOGGER.debug("Keyword queue is NOT relevant")
                    intermediate_decode = ""
                sleep(lurker_keyword_interval_seconds)
            if keyword in intermediate_decode:
                LOGGER.info("Found keyword '%s' in '%s'", keyword, intermediate_decode)
                return True
            return False

    def _record_instruction(self) -> str:
        with ((self._start_new_input_audio_stream(self._fill_instruction_queue))):
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

    def _is_keyword_queue_relevant(self, bucket_count: int = 60,
                                   start_end_silence_ratio: float = 0.1,
                                   required_bucket_ratio: float = 0.1) -> bool:
        """
        Relevant means that at the start and end of the queue is silent and least an appropriate amount of buckets
        possesses an average of absolute amplitude above the threshold.

        threshold: 50
        -----start silence----|                                                                 |-------end silence----
            12           11        18         77          155       41        51          19
        |##########|##########|##########|##########|##########|##########|##########|##########|          |          |
        0          1          2          3          4          5          6          7          8          9
                                         |---above--|---above--|          |---above--|
        """
        length = len(self.keyword_queue)
        max_length = self.keyword_queue.maxlen
        if length < max_length / 3:
            return False
        if start_end_silence_ratio < 0 or start_end_silence_ratio > 1:
            raise ValueError("start_end_silence_ratio must be in [0, 1]: " + str(start_end_silence_ratio))

        arr = np.array(self.keyword_queue)
        interval_length = int(max_length / bucket_count)

        LOGGER.debug("\n\n" + _display_to_str(self.keyword_queue, bucket_count, silence_threshold=self.silence_threshold))

        # check for start and end silence
        required_silence_bucket_count = round(bucket_count * start_end_silence_ratio)
        for i in (list(range(0, required_silence_bucket_count))
                  + list(range(bucket_count - required_silence_bucket_count, bucket_count))):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = np.abs(arr[lower: upper]).mean()
            if bucket_mean > self.silence_threshold:
                # not enough silence
                LOGGER.debug("Not enough silence when computing mean in bucket %s: %s of required %s", i, bucket_mean, self.silence_threshold)
                LOGGER.debug("\nFALSE:Not enough silence")
                return False

        # check bucket count above threshold
        threshold_breaking_buckets = 0
        for i in range(bucket_count):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = np.abs(arr[lower: upper]).mean()
            if bucket_mean > self.silence_threshold:
                threshold_breaking_buckets += 1
        is_bucket_ratio_satisfied = threshold_breaking_buckets > bucket_count * required_bucket_ratio
        LOGGER.debug("\n" + ("TRUE: Ration satisfied" if is_bucket_ratio_satisfied else "FALSE: Ratio satisfied")
                              + " " + str(threshold_breaking_buckets) + "/" + str(int(bucket_count * required_bucket_ratio)))
        return is_bucket_ratio_satisfied

    # TODO: Dynamic threshold with minimum gate
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
        interval_length = int(length / bucket_count)
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


def _display_to_str(queue: Collection, bucket_count: int, silence_threshold: int, bucket_str_length: int = 3) -> str:
    interval_length = int(len(queue) / bucket_count)
    arr = np.array(queue)

    index_line = "|"
    threshold_line = "|"
    mean_line = "|"
    for i in range(bucket_count):
        lower = i * interval_length
        upper = (i + 1) * interval_length
        if not upper < len(arr):
            break
        mean = round(np.abs(arr[lower: upper]).mean())
        index_line += "{}|".format(str(i).center(bucket_str_length, "-"))
        threshold_line += "{}|".format("#" * bucket_str_length if mean > silence_threshold else " " * bucket_str_length)
        mean_line += "{}|".format(str(min(mean, 10 ** bucket_str_length - 1)).center(bucket_str_length))
    return index_line + "\n" + threshold_line + "\n" + mean_line
