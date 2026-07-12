from collections import deque
from typing import Protocol, Any

import numpy as np
import sounddevice as sd
import webrtcvad

from src import log
from src.config import SpeechConfig

LOGGER = log.new_logger(__name__)

class ASRBackend(Protocol):
    def feed_data(self, pcm_bytes: bytes) -> None:
        """
        Push raw PCM audio into the ASR backend.
        """
        ...

    def flush(self) -> None:
        """
        Flush accumulated transcription at sentence boundary.
        """
        ...

    def reset(self) -> None:
        """
        Reset internal ASR state (start of new utterance/session).
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
        self._last_non_speech_chunk_count = 0
        self._gate_chunk_count = 0
        self._max_open_gate_chunks = int(self._capture_config.max_open_gate_seconds / (self._capture_config.frame_ms / 1000))
        self._lingering_chunks: deque[bytes] = deque(maxlen=self._capture_config.lingering_speech_chunks)
        self._audio_stream = None
        self._vad = webrtcvad.Vad(self._capture_config.vad_aggressiveness)

        self._running = False

    def start_listening(self):
        if self._running:
            return

        self._running = True

        self._audio_stream = sd.InputStream(
            samplerate=self._capture_config.sample_rate,
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
        | DOWN   | yes     | —           | reset ASR, feed lingering+current |
        | DOWN   | no      | —           | append to lingering               |
        | UP     | *       | > max       | force flush, close gate           |
        | UP     | yes     | ≤ max       | feed current, increment           |
        | UP     | no      | ≤ max       | feed current, inc silence counter |
        | UP     | no      | > silence   | close gate, return                |
        +--------+---------+-------------+----------------------------------+
        """
        if not self._running:
            return

        incoming = indata.tobytes()
        is_speech = self._call_vad(incoming)
        LOGGER.trace("chunk: bytes=%d, vad=%s, gate=%s", len(incoming), is_speech, "UP" if self._gate else "DOWN")

        if self._gate == self.GateState.DOWN:
            if is_speech:
                self._open_gate()
                lingering = len(self._lingering_chunks)
                for chunk in self._lingering_chunks:
                    self._asr.feed_data(chunk)
                self._asr.feed_data(incoming)
                LOGGER.trace("gate UP: pushed %d lingering + 1 current chunk (%d bytes total)", lingering + 1, sum(len(c) for c in self._lingering_chunks) + len(incoming))
            else:
                self._lingering_chunks.append(incoming)
                LOGGER.trace("gate DOWN: appended %d bytes to lingering (%d chunks)", len(incoming), len(self._lingering_chunks))
            return

        # gate is UP
        self._gate_chunk_count += 1
        if self._gate_chunk_count > self._max_open_gate_chunks:
            LOGGER.trace("gate force-close: exceeded max open gate chunks (%d)", self._max_open_gate_chunks)
            self._close_gate()
            return

        if not is_speech:
            self._last_non_speech_chunk_count += 1
            if self._last_non_speech_chunk_count > self._capture_config.required_trailing_silence_chunks:
                LOGGER.trace("gate close: trailing silence exceeded (%d > %d)", self._last_non_speech_chunk_count, self._capture_config.required_trailing_silence_chunks)
                self._close_gate()
                return
        else:
            self._last_non_speech_chunk_count = 0

        self._asr.feed_data(incoming)
        LOGGER.trace("fed %d bytes to ASR (silence_count=%d, gate_chunks=%d)", len(incoming), self._last_non_speech_chunk_count, self._gate_chunk_count)

    def _open_gate(self):
        self._gate = self.GateState.UP
        self._last_non_speech_chunk_count = 0
        self._gate_chunk_count = 0
        self._asr.reset()

    def _close_gate(self):
        self._asr.flush()
        self._gate = self.GateState.DOWN

    def _call_vad(self, pcm_bytes: bytes) -> bool:
        # pcm_bytes always matches frame_samples * 2 — guaranteed by the audio callback's blocksize
        return self._vad.is_speech(pcm_bytes, sample_rate=self._capture_config.sample_rate)
