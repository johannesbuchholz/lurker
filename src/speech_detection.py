import numpy as np
import webrtcvad

from src import log
from src.config import SpeechDetectorConfig

LOGGER = log.new_logger(__name__)


def _compute_energy(pcm_bytes: bytes) -> float:
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


class SpeechDetector:
    """
    Combines an energy-based pre-filter with WebRTC VAD.
    The energy filter maintains an adaptive noise floor estimate
    and only passes chunks to VAD when energy exceeds a dynamic threshold.
    """

    def __init__(self, config: SpeechDetectorConfig):
        self._sample_rate = config.sample_rate
        self._energy_factor = config.energy_factor
        self._energy_alpha = config.energy_alpha
        self._ambient_level = 0.0
        self._initialized = False
        self._vad = webrtcvad.Vad(config.vad_aggressiveness)

    def is_speech(self, pcm_bytes: bytes) -> bool:
        energy = _compute_energy(pcm_bytes)

        if not self._initialized:
            self._ambient_level = energy
            self._initialized = True

        threshold = self._ambient_level * self._energy_factor
        is_loud_enough = energy > threshold

        if not is_loud_enough:
            self._update_ambient(energy)
            return False

        is_vad_speech = self._vad.is_speech(pcm_bytes, sample_rate=self._sample_rate)
        if not is_vad_speech:
            self._update_ambient(energy)
        return is_vad_speech

    def _update_ambient(self, energy: float) -> None:
        """Track noise floor via exponential moving average."""
        self._ambient_level = self._energy_alpha * energy + (1 - self._energy_alpha) * self._ambient_level
