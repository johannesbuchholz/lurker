import importlib.util
import os
import sys
from typing import Optional

from src import config
from src import log
from src.action import ActionRegistry, ActionHandler
from src.config import LurkerConfig
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
    if i is not None and i + 1 < len(sys.argv):
        return os.path.abspath(sys.argv[i + 1])
    else:
        return os.getcwd() + "/lurker"


def _load_external_handler_module(module_path: Optional[str]) -> None:
    """
    If the module contains a class extending ActionHandler, that class will trigger
    __init__subclass of ActionHandler and thereby be registered.
    """
    if module_path is None:
        return

    # load module
    module_name_to_be_imported = "exthandler"
    spec = importlib.util.spec_from_file_location(module_name_to_be_imported, module_path)
    extmodule = importlib.util.module_from_spec(spec)
    if module_name_to_be_imported in sys.modules.keys():
        raise ValueError(f"Could not add dynamically loaded module {module_name_to_be_imported} to modules: It already exists in {sys.modules.keys()}")
    sys.modules[module_name_to_be_imported] = extmodule
    spec.loader.exec_module(extmodule)

if __name__ == "__main__":
    lurker_home_dir = _determine_lurker_home()
    LOGGER.info(f"Determined lurker home: {lurker_home_dir}", )

    LOGGER.info("Loading configuration")
    lurker_config: LurkerConfig = config.load_lurker_config(lurker_home_dir + "/config.json")
    LOGGER.info(f"Loaded configuration:\n{lurker_config.to_pretty_str()}")

    log.init_global_config(lurker_config.LURKER_LOG_LEVEL)

    LOGGER.info("Loading action handlers")
    _load_external_handler_module(lurker_config.LURKER_HANDLER_PATH)
    handler_class = ActionHandler.implementation
    handler = handler_class(**lurker_config.LURKER_HANDLER_CONFIG)
    LOGGER.info("Created handlers: %s", type(handler))

    LOGGER.info("Setting up actions")
    actions_path = lurker_home_dir + "/actions"
    registry = ActionRegistry(actions_path)
    registry.load_actions()

    orchestrator = Orchestrator(registry, handler, output_device_name=lurker_config.LURKER_OUTPUT_DEVICE)
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
        LOGGER.error(f"Fatal error: {e}", exc_info=e)
        exit(1)
