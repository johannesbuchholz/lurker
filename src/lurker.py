import os
import signal
from typing import Callable

from src import log, sound
from src.actions.action import ActionGenerator, NOPHandler, DummyHandler, ActionHandler
from src.config import LurkerConfig
from src.keyword import Keyword
from src.speech import SpeechToTextListener
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)


def _make_act_callback(registry: ActionGenerator, handler: ActionHandler, output_device_name: str | None) -> Callable[[str], None]:
    """
    Builds the callback that bridges ASR output to action execution.

    Exists as a factory (rather than a lambda in get_new) because:
    - The returned closure captures a single logger instance, avoiding per-call logger creation.
    - A named function provides a meaningful name in stack traces instead of <lambda>.
    """
    logger = log.new_logger("act")

    def act(instruction: str) -> None:
        sound.play_understood(output_device_name)
        logger.info(f"Trying to find action for instruction '{instruction}'")
        state = handler.get_state()
        lights = registry.generate_lights(instruction, state=state)
        if lights is None or len(lights) < 1:
            logger.info(f"Could not find action for instruction '{instruction}'")
            sound.play_no(output_device_name)
        else:
            logger.debug(f"Found action for instruction {instruction}: action={lights}")
            try:
                handler_exit_code = handler.handle(lights)
            except Exception as e:
                logger.error(f"Unhandled exception when handling instruction {instruction}: {type(e)} {e}", exc_info=e)
                handler_exit_code = 1

            if handler_exit_code == 0:
                logger.info(f"Successfully acted on instruction: {instruction}")
                sound.play_ok(output_device_name)
            else:
                logger.info(f"Could not act on instruction: instruction={instruction}, handler_exit_code={handler_exit_code}")
                sound.play_no(output_device_name)

    return act


class Lurker:
    """
    Ties different services together in order to act upon incoming instructions.
    """

    def __init__(self,
                 registry: ActionGenerator,
                 handler: ActionHandler,
                 listener: SpeechToTextListener,
                 input_device_name: str | None,
                 output_device_name: str | None
                 ):
        self._logger = log.new_logger(self.__class__.__name__)
        self.registry = registry
        self.handler = handler
        self.listener = listener
        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

    def start_main_loop(self) -> None:
        LOGGER.info("Initializing...")
        sound.load_sounds()

        LOGGER.info("Start listening...")
        sound.play_startup(self.output_device_name)
        try:
            self.listener.start_listening()
            signal.pause()
        except Exception as e:
            LOGGER.error(f"Fatal error: {e}", exc_info=e)
            exit(1)


def _resolve_speech_model(lurker_home: str, language: str, suffix_filter: str = "") -> str:
    """Resolve the model matching the language infix with the highest version."""
    models_dir = os.path.join(lurker_home, "models", "vosk")
    lang_infix = f"-{language.lower()}-"
    # alphabetically ascending; since versions sort numerically within a name
    matches = sorted(os.listdir(models_dir))
    for entry in matches:
        if lang_infix not in entry:
            continue
        if suffix_filter and not entry.endswith(suffix_filter):
            continue
        return os.path.join(models_dir, entry)
    raise ValueError(
        f"No model found for language '{language}' in {models_dir}: available={list(os.listdir(models_dir))}"
    )


def _resolve_handler(lurker_home: str, lurker_config: LurkerConfig) -> ActionHandler:
    """
    Resolve the configured action handler from the predefined keywords ``NOOP``, ``DUMMY`` and ``HUE``.
    Unknown values fall back to ``NOOP`` with a warning.
    """
    keyword = lurker_config.LURKER_HANDLER_MODULE.strip().upper()
    if keyword == "NOOP":
        return NOPHandler()
    if keyword == "DUMMY":
        return DummyHandler()
    if keyword == "HUE":
        from src.handlers.hue_client import HueClient
        handler_type = HueClient
    else:
        LOGGER.warning(
            f"LURKER_HANDLER_MODULE value '{lurker_config.LURKER_HANDLER_MODULE}' is not a predefined handler keyword "
            f"(NOOP, DUMMY, HUE); using NOPHandler instead."
        )
        return NOPHandler()
    # inject lurker_home into handler configuration
    handler_config_with_home = {"lurker_home": lurker_home} | lurker_config.LURKER_HANDLER_CONFIG
    try:
        return handler_type(**handler_config_with_home)
    except Exception as e:
        LOGGER.warning(f"Could not instantiate handler {handler_type}: {type(e)} {e} - Using NOPHandler instead.", exc_info=e)
        return NOPHandler()


def get_new(lurker_home: str, lurker_config: LurkerConfig) -> Lurker:
    """
    Blocks this thread.
    """

    handler = _resolve_handler(lurker_home, lurker_config)

    # resolve llm model
    embedding_model_path = _resolve_embedding_model_path(lurker_home)
    action_generator = ActionGenerator(model_path=embedding_model_path, initial_state=handler.get_state())

    model_path = _resolve_speech_model(lurker_home, lurker_config.LURKER_LANGUAGE, lurker_config.LURKER_SPEECH_MODEL_SUFFIX)
    keyword = Keyword(lurker_config.LURKER_KEYWORD)

    act_callback = _make_act_callback(action_generator, handler, lurker_config.LURKER_OUTPUT_DEVICE)
    transcriber = Transcriber(
        keyword=keyword,
        model_path=model_path,
    )
    listener = SpeechToTextListener(
        transcriber=transcriber,
        instruction_callback=act_callback,
        input_device_name=lurker_config.LURKER_INPUT_DEVICE,
        output_device_name=lurker_config.LURKER_OUTPUT_DEVICE,
        speech_config=lurker_config.LURKER_SPEECH_CONFIG,
    )

    return Lurker(
        registry=action_generator,
        handler=handler,
        listener=listener,
        input_device_name=lurker_config.LURKER_INPUT_DEVICE,
        output_device_name=lurker_config.LURKER_OUTPUT_DEVICE
    )


def _resolve_embedding_model_path(lurker_home: str) -> str:
    """A separate model for tests to call"""
    return os.path.join(lurker_home, "models", "onnx", "paraphrase-multilingual-MiniLM-L12-v2")
