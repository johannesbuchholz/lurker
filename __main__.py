import os

from src import log
from src.action_registry import HueActionRegistry
from src.client import HueClient
from src.speech import SpeechToTextListener

KEYWORD = os.environ["LURKER_KEY_WORD"].lower() if "LURKER_KEY_WORD" in os.environ else "hey john"

LOGGER = log.new_logger("Lurker ({})".format(__name__))


if __name__ == "__main__":
    LOGGER.info("Setting up hue client")
    hue_client = HueClient()
    registry = HueActionRegistry(hue_client)

    LOGGER.info("Start listening...")
    listener = SpeechToTextListener(
        model_path="resources/models/output_graph.pbmm",
        scorer_path="resources/models/kenlm.scorer",
        instruction_callback=lambda instruction: registry.act(instruction))
    listener.start_listening(key_word=KEYWORD)

    input()
    exit(0)
