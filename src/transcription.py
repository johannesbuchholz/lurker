import json
from collections import deque

from vosk import Model, KaldiRecognizer


class Transcriber:

    def __init__(self, model_path: str, sample_rate: int = 16000, max_words: int = 200):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.recognizer.SetWords(True)

        # bounded word-level buffer
        self._transcription: deque[str] = deque(maxlen=max_words)

    def feed_data(self, pcm_bytes: bytes) -> None:
        if self.recognizer.AcceptWaveform(pcm_bytes):
            self._on_final(self.recognizer.Result())

    def _on_final(self, result_str: str):
        try:
            result = json.loads(result_str)
        except Exception:
            return

        text = result.get("text", "").strip()
        if text:
            self._push_text(text)

    def reset(self) -> None:
        self.recognizer.Reset()
        self._transcription.clear()

    def _push_text(self, text: str) -> None:
        incoming = text.split()
        if len(incoming) == 0:
            return
        self._transcription.extend(incoming)

    def get_text(self) -> str:
        return " ".join(self._transcription)
