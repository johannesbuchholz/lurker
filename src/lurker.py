import importlib
import sys
from typing import Optional

from src import log, sound
from src.action import ActionRegistry, ActionHandler, LoadedHandlerType
from src.config import LurkerConfig
from src.speech import SpeechToTextListener
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)


class Lurker:
    """
    Ties different services together in order to act upon incoming instructions.
    """

    def __init__(self,
                 registry: ActionRegistry,
                 handler: ActionHandler,
                 listener: SpeechToTextListener,
                 input_device_name: str,
                 output_device_name: str
                 ):
        self._logger = log.new_logger(self.__class__.  __name__)
        self.registry = registry
        self.handler = handler
        self.listener = listener
        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

    def act(self, instruction: str) -> None:
        finding = self.registry.find(instruction)
        if finding is None:
            self._logger.info(f"Could not find action for instruction '{instruction}'")
            sound.play_no(self.output_device_name)
        else:
            action, match = finding
            self._logger.debug(f"Found action for instruction {instruction}: action={action}, match={match}")
            sound.play_understood(self.output_device_name)
            try:
                is_success = self.handler.handle(action, match)
            except Exception as e:
                self._logger.error(f"Unhandled exception when handling instruction {instruction}: {type(e)} {e}", exc_info=e)
                is_success = False

            if is_success:
                self._logger.info(f"Successfully acted on instruction: {instruction}")
                sound.play_ok(self.output_device_name)
            else:
                self._logger.info(f"Could not act on instruction: {instruction}")
                sound.play_no(self.output_device_name)

    def start_listen_loop(self, keyword: str) -> None:
        LOGGER.info("Initializing...")#
        self.registry.load_actions_once()
        self.registry.start_periodic_reloading_in_background(interval_duration_s=5)
        sound.load_sounds()

        LOGGER.info("Start listening...")
        sound.play_startup(self.output_device_name)
        try:
            self.listener.start_listening(keyword=keyword, instruction_callback=self.act)
        except Exception as e:
            LOGGER.error(f"Fatal error: {e}", exc_info=e)
            exit(1)


def _load_external_handler_module(module_name: Optional[str]) -> None:
    """
    If the module contains a class extending ActionHandler, that class will trigger
    __init_subclass__ of ActionHandler and thereby be registered.
    """
    if module_name is None:
        return
    elif module_name in sys.modules.keys():
        LOGGER.warning(f"Could not add dynamically loaded module {module_name} to modules: It already exists in sys.modules.keys()")
        return
    # load module
    extmodule = importlib.import_module(module_name)
    sys.modules[module_name] = extmodule
    LOGGER.debug(f"Loaded external module {extmodule}")


def get_new(lurker_home: str, lurker_config: LurkerConfig) -> Lurker:
    """
    Blocks this thread.
    """

    _load_external_handler_module(lurker_config.LURKER_HANDLER_MODULE)

    handler_type = LoadedHandlerType.get_implementation()
    handler_config_with_home = {"lurker_home": lurker_home} | lurker_config.LURKER_HANDLER_CONFIG
    handler = handler_type(**handler_config_with_home)
    LOGGER.info("Loaded action handler: %s", type(handler))

    actions_path = lurker_home + "/actions"
    registry = ActionRegistry(actions_path)

    transcriber = Transcriber(
        model_path=lurker_config.LURKER_MODEL,
        spoken_language=lurker_config.LURKER_LANGUAGE
    )
    listener = SpeechToTextListener(
        transcriber=transcriber,
        input_device_name=lurker_config.LURKER_INPUT_DEVICE,
        output_device_name=lurker_config.LURKER_OUTPUT_DEVICE,
        speech_config=lurker_config.LURKER_SPEECH_CONFIG
    )
    return Lurker(
        registry=registry,
        handler=handler,
        listener=listener,
        input_device_name=lurker_config.LURKER_INPUT_DEVICE,
        output_device_name=lurker_config.LURKER_OUTPUT_DEVICE
    )
