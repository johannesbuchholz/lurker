from __future__ import annotations

from collections import deque
from typing import Callable, Optional, Protocol, Any, TYPE_CHECKING

import numpy as np
import sounddevice as sd
import webrtcvad

from src import log
from src.config import SpeechConfig

if TYPE_CHECKING:
    from src.lurker import Keyword

NON_SPEECH_CHUNK_GATE_THRESHOLD = 6
LOGGER = log.new_logger(__name__)

class ASRBackend(Protocol):
    def feed_data(self, pcm_bytes: bytes) -> None:
        """
        Push raw PCM audio into the ASR backend.
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
                 input_device_name: Optional[str] = None,
                 output_device_name: Optional[str] = None,
                 speech_config: Optional[SpeechConfig] = None):
        self._asr = transcriber
        self._input_device_name = input_device_name
        self._output_device_name = output_device_name
        self._capture_config = speech_config or SpeechConfig()

        self._gate = self.GateState.DOWN
        self._last_non_speech_chunk_count = 0
        self._lingering_chunks: deque[bytes] = deque(maxlen=8)
        self._audio_stream = None
        self._vad = webrtcvad.Vad(self._capture_config.vad_aggressiveness)

        self._running = False

    def start_listening(self, keyword: Keyword, instruction_callback: Callable[[str], None]):
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
        | UP     | yes     | reset       | feed current                      |
        | UP     | no      | ≤ threshold | feed current (silence context)    |
        | UP     | no      | > threshold | close gate, append, return        |
        +--------+---------+-------------+----------------------------------+
        """
        if not self._running:
            return

        incoming = indata.tobytes()
        is_speech = self._call_vad(incoming)

        if self._gate == self.GateState.DOWN:
            if is_speech:
                self._open_gate()
                for chunk in self._lingering_chunks:
                    self._asr.feed_data(chunk)
                self._asr.feed_data(incoming)
            else:
                self._lingering_chunks.append(incoming)
            return

        # gate is UP
        if not is_speech:
            self._last_non_speech_chunk_count += 1
            if self._last_non_speech_chunk_count > NON_SPEECH_CHUNK_GATE_THRESHOLD:
                self._close_gate()
                self._lingering_chunks.append(incoming)
                return
        else:
            self._last_non_speech_chunk_count = 0

        self._asr.feed_data(incoming)

    def _open_gate(self):
        self._gate = self.GateState.UP
        self._last_non_speech_chunk_count = 0
        self._asr.reset()

    def _close_gate(self):
        self._gate = self.GateState.DOWN

    def _call_vad(self, pcm_bytes: bytes) -> bool:
        # pcm_bytes always matches frame_samples * 2 — guaranteed by the audio callback's blocksize
        return self._vad.is_speech(pcm_bytes, sample_rate=self._capture_config.sample_rate)
