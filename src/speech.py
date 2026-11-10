import logging
import queue
import threading
from collections import deque
from dataclasses import dataclass
from typing import Protocol, Any, Callable

import numpy as np
import numpy.typing as npt
import sounddevice as sd

from src import log
from src.config import SpeechConfig
from src.speech_detection import SpeechDetector

LOGGER = log.new_logger(__name__)
INPUT_STREAM_DTYPE = np.int16


@dataclass(frozen=True)
class AudioChunk:
    samples: npt.NDArray[INPUT_STREAM_DTYPE]
    sample_rate: int


class ASRBackend(Protocol):
    def feed_data(self, chunk: AudioChunk) -> bool:
        """
        Returns True when the backend has a final result (utterance complete).
        """
        ...

    def check_for_keyword(self) -> str | None:
        """
        Flush accumulated transcription at sentence boundary.
        Returns instruction string if keyword found, None otherwise.
        The returned instruction is normalized: lowercase, without punctuation.
        """
        ...


class SpeechToTextListener:

    _logger = log.new_logger(__qualname__)

    class GateState:
        DOWN = 0
        UP = 1

    def __init__(self, transcriber: ASRBackend,
                 instruction_callback: Callable[[str], None],
                 input_device_name: str | None = None,
                 output_device_name: str | None = None,
                 speech_config: SpeechConfig | None = None):
        self._asr = transcriber
        self._callback = instruction_callback
        self._input_device_name = input_device_name
        self._output_device_name = output_device_name
        self._capture_config = speech_config or SpeechConfig()

        self._gate = self.GateState.DOWN
        self._non_speech_chunk_count = 0
        self._open_gate_chunk_count = 0
        self._max_open_gate_chunks = int(
            self._capture_config.max_open_gate_seconds / (self._capture_config.frame_ms / 1000))
        self._silence_chunk_threshold = int(
            self._capture_config.silence_threshold_seconds / (self._capture_config.frame_ms / 1000))
        self._prefill_chunks: deque[AudioChunk] = deque(maxlen=self._capture_config.prefill_chunks)
        self._audio_stream = None
        self._audio_buffer: queue.Queue[AudioChunk] = self._new_audio_buffer()
        self._detector = SpeechDetector(self._capture_config.detector)

        self._is_running = False

    def stop(self):
        self._is_running = False
        if self._audio_stream:
            self._audio_stream.stop()
            self._audio_stream.close()

    def start_listening(self):
        """Starts audio listening and processing in background. Does not block."""
        if self._is_running:
            return

        self._is_running = True

        # start audio recording
        self._audio_stream = sd.InputStream(
            samplerate=self._capture_config.detector.sample_rate,
            channels=1,
            dtype=INPUT_STREAM_DTYPE,
            blocksize=self._capture_config.frame_samples,
            device=self._input_device_name or None,
            callback=self._buffer_audio,
        )
        self._audio_stream.start()

        # start audio processing loop
        threading.Thread(
            target=self._audio_processing_loop,
            name="lurker_audio_chunk_processing",
            daemon=True,
        ).start()

    def _audio_processing_loop(self) -> None:
        """Blocks until listening is stopped externally."""
        while True:
            if not self._is_running:
                return
            chunk = self._audio_buffer.get()

            if self._logger.isEnabledFor(log.TRACE):
                self._logger.log(log.TRACE, "Processing next audio chunk from buffer: remaining_chunks_in_buffer=%s", self._audio_buffer.qsize())
            self._process_audio_chunk(chunk)

    def _buffer_audio(self, indata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags):
        if not self._is_running:
            return
        incoming = AudioChunk(
            # reshape to mono flat chunk; copy because indata is only valid during the callback
            samples=indata.copy().reshape(-1),
            sample_rate=self._capture_config.detector.sample_rate,
        )
        try:
            self._audio_buffer.put_nowait(incoming)
        except queue.Full:
            self._logger.warning("Audio buffer overflow! Dropping audio chunk: frames_dropped=%d, buffer_queue_size=%d", frames, self._audio_buffer.qsize())

    def _process_audio_chunk(self, incoming: AudioChunk):
        incoming_raw = incoming.samples.tobytes()

        is_speech = self._detector.is_speech(incoming_raw, self._gate == self.GateState.DOWN)

        if self._gate == self.GateState.DOWN:
            if is_speech:
                self._open_gate()
                for chunk in self._prefill_chunks:
                    self._asr.feed_data(chunk)
                self._asr.feed_data(incoming)
            else:
                self._prefill_chunks.append(incoming)
                LOGGER.log(log.TRACE, "PREFILL: appended %d bytes (%d chunks)",
                           len(incoming_raw), len(self._prefill_chunks))
        else:
            # gate is UP
            self._open_gate_chunk_count += 1
            if self._open_gate_chunk_count > self._max_open_gate_chunks > 0:
                LOGGER.debug("GATE: force-close, exceeded max open gate chunks (%d)", self._max_open_gate_chunks)
                self._close_gate()
                return

            if is_speech:
                self._non_speech_chunk_count = 0
            else:
                self._non_speech_chunk_count += 1

            if self._non_speech_chunk_count > self._silence_chunk_threshold > 0:
                # enough silence: close gate
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.debug("GATE: close, trailing silence exceeded (%fs)",
                                 self._capture_config.silence_threshold_seconds)
                self._close_gate()
            else:
                is_final = self._asr.feed_data(incoming)
                if is_final:
                    LOGGER.debug("GATE: close, ASR indicates complete result")
                    self._close_gate()

    def _open_gate(self):
        self._gate = self.GateState.UP
        self._non_speech_chunk_count = 0
        self._open_gate_chunk_count = 0
        LOGGER.debug("OPEN GATE ●")

    def _close_gate(self):
        instruction = self._asr.check_for_keyword()
        self._gate = self.GateState.DOWN
        LOGGER.debug("CLOSE GATE ○")
        if instruction:
            self._callback(instruction)
            self._audio_buffer = self._new_audio_buffer()

    def _new_audio_buffer(self):
        # At least some few times longer that the actual prefill count
        return queue.Queue(max(4, self._capture_config.prefill_chunks * 8))
