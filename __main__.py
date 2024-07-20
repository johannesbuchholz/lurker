from src import log
from src.action_registry import HueActionRegistry
from src.client import HueClient
from src.config import CONFIG
from src.speech import SpeechToTextListener

LOGGER = log.new_logger("Lurker ({})".format(__name__), level=CONFIG.log_level())


if __name__ == "__main__":
    LOGGER.info("Setting up connection to hue bridge")
    hue_client = HueClient(CONFIG.host(), CONFIG.user())
    registry = HueActionRegistry(hue_client)

    listener = SpeechToTextListener(instruction_callback=registry.act)
    LOGGER.info("Start listening...")
    listener.start_listening()
