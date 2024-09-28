from collections import deque
from time import sleep
from typing import Callable, Any, Optional, Collection

import numpy as np
import sounddevice as sd

from src import log, sound
from src.text import filter_non_alnum
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)
SPEECH_BUCKET_COUNT = 60

class SpeechToTextListener:
    def __init__(self,
                 transcriber: Transcriber,
                 keyword_queue_length_seconds: float,
                 instruction_queue_length_seconds: float,
                 min_silence_threshold: int,
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
        self.min_silence_threshold = min_silence_threshold
        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

        #  seconds * samples_per_second * bits_per_sample / 8 = bytes required to store seconds of data
        #  For example: 3 seconds at 16_000 Hz at 16 bit require 96000 bytes (96 kb)
        byte_count_per_second = int(self.sample_rate * np.iinfo(self.bit_depth).bits / 8)
        self.keyword_queue = deque(maxlen=int(keyword_queue_length_seconds * byte_count_per_second))
        self.instruction_queue = deque(maxlen=int(instruction_queue_length_seconds * byte_count_per_second))
        self.is_listening = False

        self.keyword_queue_bucket_means = deque(maxlen=100)

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
                is_relevant, queue_mean = self._has_keyword_queue_leading_silence_followed_by_speech_and_silence()
                self.keyword_queue_bucket_means.append(queue_mean)
                if is_relevant:
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

    def _compute_threshold(self) -> int:
        threshold = round(max(self.min_silence_threshold, np.percentile(self.keyword_queue_bucket_means, q=0.2)))
        LOGGER.log(1, "Threshold: %s", threshold)
        return threshold

    def _has_keyword_queue_leading_silence_followed_by_speech_and_silence(self, bucket_count: int = SPEECH_BUCKET_COUNT,
                                                                          required_leading_silence_ratio: float = 0.1,
                                                                          required_speech_ratio: float = 0.2,
                                                                          required_trailing_silence_ratio: float = 0.1) -> (bool, int):
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
        length = len(self.keyword_queue)
        if length < self.keyword_queue.maxlen / 3:
            return False, 0
        if (max(required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio) > 1
                or min(required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio) < 0
                or required_leading_silence_ratio + required_speech_ratio + required_trailing_silence_ratio > 1):
            raise ValueError("Ratios must be in interval [0, 1] and their sum must be less than 1: " + str([required_leading_silence_ratio, required_speech_ratio, required_trailing_silence_ratio]))

        arr = np.abs(np.array(self.keyword_queue))
        interval_length = int(length / bucket_count)
        silence_threshold = self._compute_threshold()

        LOGGER.log(1, "\n" + _queue_to_str(self.keyword_queue, bucket_count, silence_threshold))

        required_leading_silence_buckets: int = round(bucket_count * required_leading_silence_ratio)
        required_buckets_with_speech: int = round(bucket_count * required_speech_ratio)
        required_trailing_silence_buckets: int = round(bucket_count * required_leading_silence_ratio)

        last_bucket_with_speech = None
        buckets_with_speech = 0
        last_silent_bucket = 0
        for i in range(0, bucket_count):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = arr[lower: upper].mean()
            if bucket_mean > silence_threshold:
                last_bucket_with_speech = i
                buckets_with_speech += 1
            else:
                last_silent_bucket = i
            if last_bucket_with_speech is not None and last_bucket_with_speech < required_leading_silence_buckets:
                LOGGER.log(1, "Too few leading silent buckets: current_bucket=%s, last_bucket_with_speech=%i, min_required_leading_silent_buckets=%i",
                             i, last_bucket_with_speech, required_leading_silence_buckets)
                return False, arr.mean()
            if last_bucket_with_speech is not None and buckets_with_speech > required_buckets_with_speech:
                # here if there is enough speech
                silence_length = last_silent_bucket - last_bucket_with_speech # may be negative
                if silence_length > required_trailing_silence_buckets:
                    LOGGER.log(1, "Keyword queue: current_bucket=%s, last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, silence_length=%s, required_trailing_silence_buckets=%s",
                        i, last_bucket_with_speech, buckets_with_speech, buckets_with_speech, last_silent_bucket, silence_length, required_trailing_silence_buckets)
                    return True, arr.mean()
        LOGGER.log(1, "Keyword queue is NOT relevant: Could not find silence after speech: last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, required_trailing_silence_buckets=%s",
                     last_bucket_with_speech, buckets_with_speech, required_buckets_with_speech, last_silent_bucket, required_trailing_silence_buckets)
        return False, arr.mean()

    def _has_instruction_queue_speech_followed_by_silence(self,
                                                          bucket_count: int = SPEECH_BUCKET_COUNT,
                                                          required_speech_ratio: float = 0.1,
                                                          required_silence_ratio: float = 0.2) -> bool:
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
        length = len(self.instruction_queue)
        if length < self.instruction_queue.maxlen / 3:
            return False
        if (max(required_speech_ratio, required_silence_ratio) > 1
                or min(required_speech_ratio, required_silence_ratio) < 0
                or required_speech_ratio + required_silence_ratio > 1):
            raise ValueError("Ratios must be in interval [0, 1] and their sum must be less than 1: " + str([required_speech_ratio, required_silence_ratio]))

        required_silent_buckets: int = round(bucket_count * required_silence_ratio)
        required_buckets_with_speech: int = round(bucket_count * required_speech_ratio)
        interval_length = int(length / bucket_count)
        arr = np.abs(np.array(self.instruction_queue))
        silence_threshold = self._compute_threshold()

        LOGGER.log(1, "\n" + _queue_to_str(self.instruction_queue, bucket_count, silence_threshold))

        last_bucket_with_speech = None
        buckets_with_speech = 0
        last_silent_bucket = 0
        for i in range(0, bucket_count):
            lower = i * interval_length
            upper = (i + 1) * interval_length
            if not upper < len(arr):
                break
            bucket_mean = arr[lower: upper].mean()
            if bucket_mean > silence_threshold:
                last_bucket_with_speech = i
                buckets_with_speech += 1
            else:
                last_silent_bucket = i
            if last_bucket_with_speech is not None and buckets_with_speech > required_buckets_with_speech:
                # length may be negative
                silence_length = last_silent_bucket - last_bucket_with_speech
                if silence_length > required_silent_buckets:
                    LOGGER.log(1, "Instruction queue is ready: current_bucket=%s, last_bucket_with_speech=%s, buckets_with_speech=%s, required_buckets_with_speech=%s, last_silent_bucket=%s, silence_length=%s, required_silent_buckets=%s",
                                 i, last_bucket_with_speech, buckets_with_speech, required_buckets_with_speech, last_silent_bucket, silence_length, required_silent_buckets)
                    return True
        return False


def _queue_to_str(queue: Collection, bucket_count: int, silence_threshold: int, bucket_str_length: int = 2) -> str:
    interval_length = int(len(queue) / bucket_count)
    arr = np.array(queue)

    index_line = "index |".rjust(12)
    threshold_line = "threshold |".rjust(12)
    for i in range(bucket_count):
        lower = i * interval_length
        upper = (i + 1) * interval_length
        if not upper < len(arr):
            break
        mean = round(np.abs(arr[lower: upper]).mean())
        index_line += "{}|".format(str(i).center(bucket_str_length, "-"))
        threshold_line += "{}|".format("#" * bucket_str_length if mean > silence_threshold else " " * bucket_str_length)
    return index_line + "\n" + threshold_line
