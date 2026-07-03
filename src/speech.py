import queue
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable

import sounddevice as sd
import webrtcvad
from vosk import Model, KaldiRecognizer


@dataclass
class ASRConfig:
    sample_rate: int = 16000
    frame_ms: int = 20                  # 10 - 30 ms recommended
    vad_aggressiveness: int = 2         # 0–3 (3 = most strict)


class StreamingVoiceOrchestrator:
    """
    Mic → VAD → Gate → Vosk streaming ASR

    This is the full runtime voice pipeline.
    """

    class GateState:
        DOWN = 0
        UP = 1

    def __init__(
        self,
        model_path: str,
        config: ASRConfig = ASRConfig(),
        on_final_text: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.on_final_text = on_final_text

        # --- VAD ---
        self.vad = webrtcvad.Vad(config.vad_aggressiveness)

        # --- ASR ---
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, config.sample_rate)
        self.recognizer.SetWords(True)

        # --- Audio stream ---
        self._audio_q = queue.Queue()
        self._running = False
        self._thread = None
        self._stream = None

        # --- Gate state ---
        self.gate = self.GateState.DOWN
        self._speech_ms = 0
        self._silence_ms = 0

        # --- Live buffer ---
        self._text_buffer = deque(maxlen=8000)
        self._lock = threading.Lock()

        # frame size
        self.frame_samples = int(config.sample_rate * config.frame_ms / 1000)

    def start(self, device=None):
        if self._running:
            return

        self._running = True

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_samples,
            device=device,
            callback=self._audio_callback,
        )
        self._stream.start()

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def get_text(self) -> str:
        with self._lock:
            return "".join(self._text_buffer)

    def get_snapshot(self, n=300) -> str:
        with self._lock:
            return "".join(list(self._text_buffer)[-n:])

    def _audio_callback(self, indata, frames, time, status):
        if self._running:
            self._audio_q.put(indata.copy())

    def _worker(self):
        frame_duration = self.config.frame_ms

        while self._running:
            try:
                frame = self._audio_q.get(timeout=0.1)
            except queue.Empty:
                continue

            # ensure int16 mono bytes
            pcm = frame[:, 0].tobytes()

            is_speech = self.vad.is_speech(
                pcm,
                self.config.sample_rate
            )

            if is_speech:
                self._silence_ms = 0
                self._speech_ms += frame_duration

                if self.gate == self.GateState.DOWN:
                    if self._speech_ms >= self.config.speech_start_ms:
                        self._open_gate()

            else:
                self._speech_ms = 0

                if self.gate == self.GateState.UP:
                    self._silence_ms += frame_duration
                    if self._silence_ms >= self.config.silence_end_ms:
                        self._close_gate()

            if self.gate == self.GateState.UP:
                self._feed_asr(pcm)

    def _open_gate(self):
        self.gate = self.GateState.UP
        self._speech_ms = 0
        self._silence_ms = 0

        # optional: reset recognizer for clean utterance
        self.recognizer.Reset()

    def _close_gate(self):
        self.gate = self.GateState.DOWN

        # finalize last result
        result = self.recognizer.FinalResult()
        text = self._extract_text(result)

        if text:
            self._append_text(text + " ")
            if self.on_final_text:
                self.on_final_text(text)

        self._speech_ms = 0
        self._silence_ms = 0

    def _feed_asr(self, pcm_bytes: bytes):
        if self.recognizer.AcceptWaveform(pcm_bytes):
            result = self.recognizer.Result()
            text = self._extract_text(result)

            if text:
                self._append_text(text + " ")

    def _extract_text(self, json_str: str) -> str:
        import json
        try:
            return json.loads(json_str).get("text", "").strip()
        except Exception:
            return ""

    def _append_text(self, text: str):
        with self._lock:
            for ch in text:
                self._text_buffer.append(ch)