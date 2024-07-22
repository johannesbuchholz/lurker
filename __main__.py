import os
import sys

from src import log
from src.action_registry import HueActionRegistry, load_actions
from src.client import HueClient
from src.config import LurkerConfig
from src.speech import SpeechToTextListener

LOGGER = log.new_logger(__name__)


def _determine_lurker_home() -> str:
    try:
        i = sys.argv.index("--lurker-home")
    except ValueError:
        i = None
    if i and i + 1 < len(sys.argv):
        return sys.argv[i + 1]
    else:
        return os.getcwd() + "/lurker"


if __name__ == "__main__":
    lurker_home_dir = _determine_lurker_home()
    LOGGER.info("Determined lurker home: %s", lurker_home_dir)

    LOGGER.info("Loading configuration")
    config = LurkerConfig(lurker_home_dir + "/config.json")
    LOGGER.info("Loaded configuration:\n%s", config)

    log.set_all_levels(config.log_level())

    LOGGER.info("Setting up connection to hue bridge")
    hue_client = HueClient(config.host(), config.user())

    LOGGER.info("Loading actions")
    actions = load_actions(lurker_home_dir + "/actions")
    LOGGER.info("Loaded actions: %s", len(actions))
    registry = HueActionRegistry(hue_client, actions)

    listener = SpeechToTextListener(
        instruction_callback=registry.act,
        model=config.model(),
        keyword_queue_length_seconds=config.keyword_queue_length_seconds(),
        instruction_queue_length_seconds=config.instruction_queue_length_seconds(),
        silence_threshold=config.silence_threshold(),
        input_device_name=config.input_device(),
        output_device_name=config.output_device(),
    )
    LOGGER.info("Start listening...")
    try:
        listener.start_listening(config.keyword())
    except Exception as e:
        LOGGER.error("Fatal error: %s", str(e))
        exit(1)
