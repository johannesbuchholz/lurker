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
        self._energy_alpha_attack = config.energy_alpha_attack
        self._energy_alpha_decay = config.energy_alpha_decay
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
            LOGGER.trace("ENERGY: rejected (energy=%.1f, threshold=%.1f, ambient=%.1f)", energy, threshold, self._ambient_level)
            return False

        is_vad_speech = self._vad.is_speech(pcm_bytes, sample_rate=self._sample_rate)
        if not is_vad_speech:
            self._update_ambient(energy)
            LOGGER.trace("VAD: rejected (energy=%.1f, threshold=%.1f, ambient=%.1f)", energy, threshold, self._ambient_level)
        else:
            LOGGER.trace("SPEECH: accepted (energy=%.1f, threshold=%.1f, ambient=%.1f)", energy, threshold, self._ambient_level)
        return is_vad_speech

    def _update_ambient(self, energy: float) -> None:
        """Track noise floor via asymmetric exponential moving average.
        Fast attack when energy rises, slow decay when energy falls."""
        if energy > self._ambient_level:
            alpha = self._energy_alpha_attack
        else:
            alpha = self._energy_alpha_decay
        self._ambient_level = alpha * energy + (1 - alpha) * self._ambient_level
