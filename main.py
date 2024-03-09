import os

from actions.registry import HueActionRegistry
from client import HueClient
from log import logger
from speech import SpeechToTextListener

KEYWORD = os.environ["LURKER_KEY_WORD"].lower() if "LURKER_KEY_WORD" in os.environ else "hey john"

if __name__ == "__main__":
    logger.info("Starting lurker")
    logger.info("Warming up...")

    logger.info("Setting up hue client")
    hue_client = HueClient()
    registry = HueActionRegistry(hue_client)

    logger.info("Start listening...")
    listener = SpeechToTextListener(
        model_path="deepspeech-0.9.3-models.pbmm",
        scorer_path="deepspeech-0.9.3-models.scorer",
        instruction_callback=lambda instruction: registry.act(instruction))
    listener.start_recording_in_background(key_word=KEYWORD)

    input()
    logger.info("Exit lurker")
    listener.stop_listening()
    exit(0)
