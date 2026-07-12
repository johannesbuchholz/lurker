from collections import deque
from typing import Protocol, Any

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

    def flush(self) -> None:
        """
        Flush accumulated transcription at sentence boundary.
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
                 input_device_name: str | None = None,
                 output_device_name: str | None = None,
                 speech_config: SpeechConfig | None = None):
        self._asr = transcriber
        self._input_device_name = input_device_name
        self._output_device_name = output_device_name
        self._capture_config = speech_config or SpeechConfig()

        self._gate = self.GateState.DOWN
        self._non_speech_chunk_count = 0
        self._gate_chunk_count = 0
        self._max_open_gate_chunks = int(self._capture_config.max_open_gate_seconds / (self._capture_config.frame_ms / 1000))
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
        """
        Gate logic:
        +--------+---------+-------------+----------------------------------+
        | Gate   | Speech  | Counter     | Action                           |
        +--------+---------+-------------+----------------------------------+
        | DOWN   | yes     | —           | feed prefill+current to ASR      |
        | DOWN   | no      | —           | append to prefill buffer         |
        | UP     | *       | > max       | force flush, close gate          |
        | UP     | yes     | ≤ max       | feed current, reset silence      |
        | UP     | no      | ≤ max       | feed current, inc silence counter|
        | UP     | no      | > silence   | close gate, return               |
        +--------+---------+-------------+----------------------------------+
        """
        if not self._running:
            return

        incoming = indata.tobytes()
        is_speech = self._detector.is_speech(incoming)

        if self._gate == self.GateState.DOWN:
            if not is_speech:
                self._prefill_chunks.append(incoming)
                LOGGER.trace("PREFILL: appended %d bytes (%d chunks)", len(incoming), len(self._prefill_chunks))
                return
            self._open_gate()
            prefill = len(self._prefill_chunks)
            for chunk in self._prefill_chunks:
                self._asr.feed_data(chunk)
            self._asr.feed_data(incoming)
            LOGGER.trace("GATE: opened, pushed %d prefill + 1 current chunk (%d bytes total)", prefill + 1, sum(len(c) for c in self._prefill_chunks) + len(incoming))
            return

        # gate is UP
        self._gate_chunk_count += 1
        if self._gate_chunk_count > self._max_open_gate_chunks:
            LOGGER.trace("GATE: force-close, exceeded max open gate chunks (%d)", self._max_open_gate_chunks)
            self._close_gate()
            return

        if not is_speech:
            self._non_speech_chunk_count += 1
            if self._non_speech_chunk_count > self._capture_config.required_trailing_silence_chunks > 0:
                LOGGER.trace("GATE: close, trailing silence exceeded (%d > %d)", self._non_speech_chunk_count, self._capture_config.required_trailing_silence_chunks)
                self._close_gate()
                return
        else:
            self._non_speech_chunk_count = 0

        is_final = self._asr.feed_data(incoming)
        if is_final:
            LOGGER.debug("GATE: close, Vosk returned final result")
            self._close_gate()

    def _open_gate(self):
        self._gate = self.GateState.UP
        self._non_speech_chunk_count = 0
        self._gate_chunk_count = 0
        LOGGER.debug("OPEN GATE ●")

    def _close_gate(self):
        self._asr.flush()
        self._gate = self.GateState.DOWN
        LOGGER.debug("CLOSE GATE ○")
