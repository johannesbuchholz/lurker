from collections import deque
from dataclasses import dataclass
from typing import Protocol, Any

import numpy as np
import sounddevice as sd
import webrtcvad

import log

NON_SPEECH_CHUNK_GATE_THRESHOLD = 6


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

@dataclass
class ASRConfig:
    sample_rate: int = 16000
    frame_ms: int = 20
    vad_aggressiveness: int = 2
    frame_samples: int = None

    def __post_init__(self):
        # Validate and adjust sample rate for WebRTC VAD
        valid_rates = [8000, 16000, 32000, 48000]
        if self.sample_rate not in valid_rates:
            import log
            logger = log.new_logger(__qualname__)
            logger.warning(
                f"Sample rate {self.sample_rate} not optimal for WebRTC VAD. "
                f"Using 16000 instead. Valid rates: {valid_rates}"
            )
            self.sample_rate = 16000

        # Calculate frame samples if not provided
        if self.frame_samples is None:
            self.frame_samples = int(self.sample_rate * (self.frame_ms / 1000))


class StreamingVoiceOrchestrator:
    """
    Mic → VAD (external) → Gate → ASR (abstracted backend)
    """

    _logger = log.new_logger(__qualname__)

    class GateState:
        DOWN = 0
        UP = 1

    def __init__(self, asr_backend, config=None):
        self._asr = asr_backend
        self._capture_config = config or ASRConfig()

        self._gate = self.GateState.DOWN
        self._last_non_speech_chunk_count = 0
        self._lingering_chunks: deque[bytes] = deque(maxlen=8)
        self._audio_stream = None
        self._vad = webrtcvad.Vad(config.vad_aggressiveness)

        self._running = False

    def start(self, device=None):
        if self._running:
            return

        self._running = True

        self._audio_stream = sd.InputStream(
            samplerate=self._capture_config.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._capture_config.frame_samples,
            device=device,
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
