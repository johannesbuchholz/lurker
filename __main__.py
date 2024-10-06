import os
import sys

from src import config
from src import log
from src.action import ActionRegistry, ActionHandler
from src.config import LurkerConfig
from src.external.client import HueClient
from src.management import Orchestrator
from src.sound import play_ready
from src.speech import SpeechToTextListener
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)


def _determine_lurker_home() -> str:
    try:
        i = sys.argv.index("--lurker-home")
    except ValueError:
        i = None
    if i and i + 1 < len(sys.argv):
        return os.path.abspath(sys.argv[i + 1])
    else:
        return os.getcwd() + "/lurker"


if __name__ == "__main__":
    lurker_home_dir = _determine_lurker_home()
    LOGGER.info("Determined lurker home: %s", lurker_home_dir)

    LOGGER.info("Loading configuration")
    lurker_config: LurkerConfig = config.load_lurker_config(lurker_home_dir + "/config.json")
    LOGGER.info("Loaded configuration:\n%s", lurker_config.to_pretty_str())

    log.init_global_config(lurker_config.LURKER_LOG_LEVEL)

    # TODO: Implement dynamic loading of ActionHandler
    LOGGER.info("Setting up connection to hue bridge")
    hue_client: ActionHandler = HueClient(**lurker_config.LURKER_HANDLER_CONFIG)

    LOGGER.info("Setting up actions")
    actions_path = lurker_home_dir + "/actions"
    registry = ActionRegistry(actions_path)
    registry.load_actions()

    orchestrator = Orchestrator(registry, hue_client, output_device_name=lurker_config.LURKER_OUTPUT_DEVICE)
    transcriber = Transcriber(model_path=lurker_config.LURKER_MODEL, spoken_language=lurker_config.LURKER_LANGUAGE)

    listener = SpeechToTextListener(
        transcriber=transcriber,
        input_device_name=lurker_config.LURKER_INPUT_DEVICE,
        output_device_name=lurker_config.LURKER_OUTPUT_DEVICE,
        instruction_callback=orchestrator.act,
        **lurker_config.LURKER_SPEECH_CONFIG.__dict__
    )

    LOGGER.info("Start listening...")
    play_ready(lurker_config.LURKER_OUTPUT_DEVICE)
    try:
        listener.start_listening(lurker_config.LURKER_KEYWORD)
    except Exception as e:
        LOGGER.error("Fatal error: %s", str(e), exc_info=e)
        exit(1)
