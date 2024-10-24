import math
from collections import deque
from time import sleep
from typing import Callable, Any, Optional, Collection

import numpy as np
import sounddevice as sd

from src import log, sound
from src.config import SpeechConfig
from src.text import filter_non_alnum
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)

class SpeechToTextListener:
    def __init__(self,
                 transcriber: Transcriber,
                 input_device_name: Optional[str],
                 output_device_name: Optional[str],
                 speech_config: SpeechConfig,
                 ):
        self._logger = log.new_logger(self.__class__.__name__)
        self.transcriber = transcriber

        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

        self.speech_config = speech_config

        self.sample_rate = 16_000
        self.bit_depth = np.dtype(np.int16)
        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(self.speech_config.keyword_queue_length_seconds * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(self.speech_config.instruction_queue_length_seconds * byte_count_per_second))
        self.is_listening = False

        self.keyword_queue_bucket_means = deque(maxlen=100)

    def start_listening(self, keyword: str, instruction_callback: Callable[[str], None]):
        """
        Blocks this thread.
        :param keyword: A sequence of words to mark start instruction recording.
        :param instruction_callback: A callable acting on some instruction string. Returns a boolean to indicate if
        acting on the instruction has been successful.
        """
        if keyword is None:
            raise ValueError("Keyword can not be None")
        if self.is_listening:
            self._logger.debug("Already listening.")
            return
        self._logger.info("Start recording using keyword '%s'", keyword)

        self.is_listening = True
        while self.is_listening:
            if self._wait_for_keyword(keyword):
                sound.play_ready(self.output_device_name)
                instruction = self._record_instruction()
                self._logger.info("Extracted instruction: %s", instruction)
                self._clear_queues()
                instruction_callback(instruction)


    def stop_listening(self):
        self.is_listening = False

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

    def _wait_for_keyword(self, keyword: str) -> bool:
        with self._start_new_input_audio_stream(self._fill_keyword_queue):
            intermediate_decode: str = ""
            while self.is_listening and (intermediate_decode == "" or keyword not in intermediate_decode):
                self._logger.debug("Did not find keyword '%s' in '%s'", keyword, intermediate_decode)
                is_relevant, queue_mean = _has_keyword_queue_leading_silence_followed_by_speech_and_silence(
                    self.keyword_queue,
                    self._compute_silence_threshold(self.speech_config.ambiance_level_factor),
                    self.speech_config.speech_bucket_count,
                    self.speech_config.required_leading_silence_ratio,
                    self.speech_config.required_speech_ratio,
                    self.speech_config.required_trailing_silence_ratio)
                self.keyword_queue_bucket_means.append(queue_mean)
                if is_relevant:
                    transcription = self.transcriber.transcribe(self.keyword_queue)
                    intermediate_decode = filter_non_alnum(transcription)
                else:
                    intermediate_decode = ""
                sleep(self.speech_config.queue_check_interval_seconds)
            if keyword in intermediate_decode:
                self._logger.info("Found keyword '%s' in '%s'", keyword, intermediate_decode)
                return True
            return False

    def _record_instruction(self) -> str:
        with ((self._start_new_input_audio_stream(self._fill_instruction_queue))):
            self._logger.debug("Waiting for action queue to be filled: queue_length_byte={}"
                         .format(self.instruction_queue.maxlen))
            while (self.is_listening
                   and not _has_instruction_queue_speech_followed_by_silence(
                        self.instruction_queue,
                        self._compute_silence_threshold(self.speech_config.ambiance_level_factor),
                        self.speech_config.speech_bucket_count,
                        self.speech_config.required_speech_ratio,
                        self.speech_config.required_trailing_silence_ratio)
                   and (len(self.instruction_queue) < self.instruction_queue.maxlen)):
                sleep(self.speech_config.queue_check_interval_seconds)
            recorded_instruction: str = filter_non_alnum(self.transcriber.transcribe(self.instruction_queue))
            self._logger.debug("Recorded instruction: sample_count={}, text={}".format(len(self.instruction_queue), recorded_instruction))
            return recorded_instruction

    def _clear_queues(self) -> None:
        self.keyword_queue.clear()
        self.instruction_queue.clear()

    def _compute_silence_threshold(self, ambiance_level_factor: float) -> int:
        if len(self.keyword_queue) > 0:
            ambiance_level_median = round(np.median(self.keyword_queue_bucket_means))
        else:
            ambiance_level_median = 0

        factorized_threshold = round(ambiance_level_median * ambiance_level_factor)
        threshold = max(self.speech_config.min_silence_threshold, factorized_threshold)
        self._logger.log(1, f"Compute silence threshold: ambiance_level_median * ambiance_level_factor = {ambiance_level_median} * {ambiance_level_factor} = {factorized_threshold} -> threshold {threshold}")
        return threshold


def _has_keyword_queue_leading_silence_followed_by_speech_and_silence(data: Collection[int], silence_threshold: int, bucket_count: int,
                                                                      required_leading_silence_ratio: float,
                                                                      required_speech_ratio: float,
                                                                      required_trailing_silence_ratio: float) -> (bool, int):
    """
    Relevant means that at the start and end of the queue is silent and least an appropriate amount of buckets
    possesses an average of absolute amplitude above the threshold.


                        Silence lead           Silence tail 1       Silence tail 2
                                       Speech
                        |-------------|-------|---------|          |----------------|
                                         #
                                        ####                 ###
       threshold: --------------------########----------###########-------------------------------------
                                   ##############     ##############              ##
                                 ##################  ################            #####
                t -----|---------------------------------------------------------------------|---------->
                       ^                                                                  ^
                       queue start                                                        queue end
    :return tuple <is relevant>, <keyword queue abs mean>
    """
    if len(data) < 1:
        return False, 0
    if (max(required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio) > 1
            or min(required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio) < 0
            or required_leading_silence_ratio + required_speech_ratio + required_trailing_silence_ratio > 1):
        raise ValueError("Ratios must be in interval [0, 1] and their sum must be less than 1: " + str([required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio]))

    arr = np.abs(np.array(data))
    interval_length = math.floor(len(arr) / bucket_count)


    LOGGER.log(1, "\n" + _queue_to_str(arr, bucket_count, silence_threshold))

    required_leading_silence_buckets: int = round(bucket_count * required_leading_silence_ratio)
    required_buckets_with_speech: int = round(bucket_count * required_speech_ratio)
    required_trailing_silence_buckets: int = round(bucket_count * required_leading_silence_ratio)
    last_bucket_with_speech = None
    trailing_silence_length = -1
    buckets_with_speech = 0
    last_silent_bucket = 0
    for i in range(0, bucket_count):
        lower = i * interval_length
        upper = (i + 1) * interval_length
        if upper > len(arr):
            break
        bucket_mean = arr[lower: upper].mean()
        if bucket_mean >= silence_threshold:
            last_bucket_with_speech = i
            buckets_with_speech += 1
        else:
            last_silent_bucket = i
        if last_bucket_with_speech is not None and last_bucket_with_speech < required_leading_silence_buckets:
            LOGGER.log(1, "Keyword queue is NOT relevant: Too few leading silent buckets: current_bucket=%s, last_bucket_with_speech=%i, min_required_leading_silent_buckets=%i",
                         i, last_bucket_with_speech, required_leading_silence_buckets)
            return False, arr.mean()
        if last_bucket_with_speech is not None and buckets_with_speech >= required_buckets_with_speech:
            # here if there is enough speech
            trailing_silence_length = last_silent_bucket - last_bucket_with_speech # may be negative
            if trailing_silence_length >= required_trailing_silence_buckets:
                LOGGER.log(1, "Keyword queue is relevant: current_bucket=%s, last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, trailing_silence_length=%s, required_trailing_silence_buckets=%s",
                    i, last_bucket_with_speech, buckets_with_speech, buckets_with_speech, last_silent_bucket, trailing_silence_length, required_trailing_silence_buckets)
                return True, arr.mean()
    LOGGER.log(1, "Keyword queue is NOT relevant: Could not find silence after speech: last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, trailing_silence_length=%s, required_trailing_silence_buckets=%s",
                 last_bucket_with_speech, buckets_with_speech, required_buckets_with_speech, last_silent_bucket, trailing_silence_length, required_trailing_silence_buckets)
    return False, arr.mean()


def _has_instruction_queue_speech_followed_by_silence(data: Collection[int],
                                                      silence_threshold: int,
                                                      bucket_count: int,
                                                      required_speech_ratio: float,
                                                      required_trailing_silence_ratio: float) -> bool:
    """
    The instruction is deemed to be spoken if some sound has been recorded followed by enough silence.

                                           speech        silence

                                           |------------|-----------------|
                                               #
                                              ####
       threshold: -------------------------#############-------------------------------------
                                        ############################                ##
                                      ##################################       ##########
                t -----|------------------------------------------------------------------|-->
                       ^                                                                  ^
                       queue start                                                        queue end
    """
    if len(data) < 1:
        return False
    if (max(required_speech_ratio, required_trailing_silence_ratio) > 1
            or min(required_speech_ratio, required_trailing_silence_ratio) < 0
            or required_speech_ratio + required_trailing_silence_ratio > 1):
        raise ValueError("Ratios must be in interval [0, 1] and their sum must be less than 1: " + str([required_speech_ratio, required_trailing_silence_ratio]))

    interval_length = math.floor(len(data) / bucket_count)
    arr = np.abs(np.array(data))

    LOGGER.log(1, "\n" + _queue_to_str(arr, bucket_count, silence_threshold))

    required_trailing_silence_buckets: int = round(bucket_count * required_trailing_silence_ratio)
    required_buckets_with_speech: int = round(bucket_count * required_speech_ratio)
    last_bucket_with_speech = None
    trailing_silence_length = -1
    buckets_with_speech = 0
    last_silent_bucket = 0
    for i in range(0, bucket_count):
        lower = i * interval_length
        upper = (i + 1) * interval_length
        if upper > len(arr):
            break
        bucket_mean = arr[lower: upper].mean()
        if bucket_mean >= silence_threshold:
            last_bucket_with_speech = i
            buckets_with_speech += 1
        else:
            last_silent_bucket = i
        if last_bucket_with_speech is not None and buckets_with_speech >= required_buckets_with_speech:
            # length may be negative
            trailing_silence_length = last_silent_bucket - last_bucket_with_speech
            if trailing_silence_length >= required_trailing_silence_buckets:
                LOGGER.log(1, "Instruction queue is ready: current_bucket=%s, last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, trailing_silence_length=%s, required_trailing_silence_buckets=%s",
                             i, last_bucket_with_speech, buckets_with_speech, required_buckets_with_speech, last_silent_bucket, trailing_silence_length, required_trailing_silence_buckets)
                return True
    LOGGER.log(1,
               "Instruction queue is NOT yet ready: last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, trailing_silence_length=%s, required_trailing_silence_buckets=%s",
               last_bucket_with_speech, buckets_with_speech, required_buckets_with_speech, last_silent_bucket, trailing_silence_length, required_trailing_silence_buckets)
    return False


def _queue_to_str(data: Collection, bucket_count: int, silence_threshold: int, bucket_str_length: int = 4) -> str:
    interval_length = math.floor(len(data) / bucket_count)
    arr = np.abs(data)

    index_line = "index |".rjust(12)
    threshold_broken_line = "threshold |".rjust(12)
    mean_line = "mean |".rjust(12)
    threshold_line = f"threshold: {silence_threshold}"
    stats_line = "percentiles [10%, 50%, 75%, 90%]: " + str(np.round(np.percentile(arr, q=[10, 50, 75, 90])))

    maximum_mean_value_to_display = 10 ** (bucket_str_length - 1) - 1
    threshold_break_str = "#" * bucket_str_length
    threshold_not_broken_str = " " * bucket_str_length

    for i in range(bucket_count):
        lower = i * interval_length
        upper = (i + 1) * interval_length
        if upper > len(arr):
            break
        mean = round(arr[lower: upper].mean())
        index_line += "{}|".format(str(i).center(bucket_str_length, "-"))
        threshold_broken_line += "{}|".format(threshold_break_str if mean > silence_threshold else threshold_not_broken_str)
        mean_line += "{}|".format(str(min(mean, maximum_mean_value_to_display)).center(bucket_str_length))

    return f"""
    {index_line}
    {threshold_broken_line}
    {mean_line}
    {threshold_line}
    {stats_line}
    """

