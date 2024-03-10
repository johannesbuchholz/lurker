import os
import time

from src import log
from src.action_registry import HueActionRegistry
from src.client import HueClient
from src.speech import SpeechToTextListener

KEYWORD = os.environ["LURKER_KEY_WORD"].lower() if "LURKER_KEY_WORD" in os.environ else "hey john"

LOGGER = log.new_logger("Lurker ({})".format(__name__))


def warmup() -> None:
    warmup_listener = SpeechToTextListener(
        model_path="resources/models/deepspeech-0.9.3-models.pbmm",
        scorer_path="resources/models/deepspeech-0.9.3-models.scorer")
    warmup_listener.start_listening("__this_is_a_warmup__")
    time.sleep(3)
    warmup_listener.stop_listening()


if __name__ == "__main__":
    LOGGER.info("Warming up...")
    warmup()

    LOGGER.info("Setting up hue client")
    hue_client = HueClient()
    registry = HueActionRegistry(hue_client)

    LOGGER.info("Start listening...")
    listener = SpeechToTextListener(
        model_path="resources/models/deepspeech-0.9.3-models.pbmm",
        scorer_path="resources/models/deepspeech-0.9.3-models.scorer",
        instruction_callback=lambda instruction: registry.act(instruction))
    listener.start_listening(key_word=KEYWORD)

    input()
    exit(0)
