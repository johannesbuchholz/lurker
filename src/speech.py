import logging
from collections import deque
from typing import Protocol, Any, Callable

import numpy as np
import sounddevice as sd

from src import log
from src.config import SpeechConfig
from src.speech_detection import SpeechDetector

LOGGER = log.new_logger(__name__)

class ASRBackend(Protocol):
    def feed_data(self, pcm_bytes: bytes) -> bool:
        """
        Push raw PCM audio into the ASR backend.
        Returns True when the backend has a final result (utterance complete).
        """
        ...

    def check_for_keyword(self) -> str | None:
        """
        Flush accumulated transcription at sentence boundary.
        Returns instruction string if keyword found, None otherwise.
        """
        ...


class SpeechToTextListener:
    """
    Mic → VAD (external) → Gate → ASR (abstracted backend)
    """

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
        self._max_open_gate_chunks = int(self._capture_config.max_open_gate_seconds / (self._capture_config.frame_ms / 1000))
        self._silence_chunk_threshold = int(self._capture_config.silence_threshold_seconds / (self._capture_config.frame_ms / 1000))
        self._prefill_chunks: deque[bytes] = deque(maxlen=self._capture_config.prefill_chunks)
        self._audio_stream = None
        self._detector = SpeechDetector(self._capture_config.detector)

        self._running = False

    def start_listening(self):
        if self._running:
            return

        self._running = True

        self._audio_stream = sd.InputStream(
            samplerate=self._capture_config.detector.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._capture_config.frame_samples,
            device=self._input_device_name or None,
            callback=self._process_audio_callback,
        )
        self._audio_stream.start()

    def stop(self):
        self._running = False
        if self._audio_stream:
            self._audio_stream.stop()
            self._audio_stream.close()

    def _process_audio_callback(self, indata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags):
        if not self._running:
            return

        incoming = indata.tobytes()
        is_speech = self._detector.is_speech(incoming, self._gate == self.GateState.DOWN)

        if self._gate == self.GateState.DOWN:
            if is_speech:
                self._open_gate()
                for chunk in self._prefill_chunks:
                    self._asr.feed_data(chunk)
                self._asr.feed_data(incoming)
                if LOGGER.isEnabledFor(log.TRACE):
                    LOGGER.log(log.TRACE, "GATE: opened, pushed %d prefill + 1 current chunk (%d bytes total)", len(self._prefill_chunks) + 1, sum(len(c) for c in self._prefill_chunks) + len(incoming))
            else:
                self._prefill_chunks.append(incoming)
                LOGGER.log(log.TRACE, "PREFILL: appended %d bytes (%d chunks)", len(incoming), len(self._prefill_chunks))
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
                    LOGGER.debug("GATE: close, trailing silence exceeded (%fs)",self._capture_config.silence_threshold_seconds)
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
        self._act_on_instruction(instruction)

    def _act_on_instruction(self, instruction: str | None) -> None:
        """Blocks until callback returns."""
        if instruction:
            self._callback(instruction)
