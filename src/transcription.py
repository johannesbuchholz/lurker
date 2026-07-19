import json

from vosk import Model, KaldiRecognizer

from src import log
from src.keyword import Keyword
from src.speech import ASRBackend


class Transcriber(ASRBackend):

    def __init__(self, keyword: Keyword, model_path: str, sample_rate: int = 16000):
        self._logger = log.new_logger(self.__class__.__name__)

        self._model = Model(model_path)
        self._recognizer = KaldiRecognizer(self._model, sample_rate)
        self._recognizer.SetWords(True)

        self._keyword = keyword

    def feed_data(self, pcm_bytes: bytes) -> bool:
        return self._recognizer.AcceptWaveform(pcm_bytes)

    def check_for_keyword(self) -> str | None:
        """
        Checks accumulated transcription for keyword and fires callback if found.
        On keyword match, resets recognizer and clears transcription.
        """
        complete_asr_result: str = self._recognizer.Result()
        if complete_asr_result:
            # asr thinks, this is a complete result.
            complete_json = {}
            try:
                complete_json = json.loads(complete_asr_result)
            except Exception as e:
                self._logger.warning(f"Could not read partial result: {complete_json} ({e})", exc_info=True)
            result_to_check = complete_json.get("text", "").strip()
        else:
            # full result not available: us current partial result
            partial_json = {}
            try:
                partial_json = json.loads(self._recognizer.PartialResult())
            except Exception as e:
                self._logger.warning(f"Could not read partial result: {partial_json} ({e})", exc_info=True)
            result_to_check = partial_json.get("partial", "").strip()

        keyword_end_index = self._keyword.is_in(result_to_check)
        instruction = None
        has_keyword = keyword_end_index is not None
        if has_keyword:
            instruction = result_to_check[keyword_end_index:].strip()
            self._recognizer.Reset()
        self._logger.debug(f"Checked: has_keyword={has_keyword}, text=\"{result_to_check}\", instruction=\"\"")
        return instruction
