import os
import signal

from src import log, sound
from src.bootstrap import Bootstrap
from src.dispatch import ActionDispatcher
from src.keyword import Keyword
from src.speech import SpeechToTextListener
from src.transcription import Transcriber

LOGGER = log.new_logger(__name__)


class Lurker:
    """
    Ties different services together in order to act upon incoming instructions.
    """

    def __init__(
            self,
            listener: SpeechToTextListener,
            output_device_name: str | None,
    ):
        self._logger = log.new_logger(self.__class__.__name__)
        self.listener = listener
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
    models_dir = os.path.join(lurker_home, "models", "onnx")
    lang_infix = f"-{language.lower()}-"
    # alphabetically ascending; since versions sort numerically within a name
    matches = sorted(os.listdir(models_dir))
    for entry in matches:
        if lang_infix not in entry:
            continue
        if suffix_filter and not suffix_filter in entry:
            continue
        return os.path.join(models_dir, entry)
    raise ValueError(
        f"No model found for language '{language}' in {models_dir}: available={list(os.listdir(models_dir))}"
    )


def get_new(startup: Bootstrap) -> Lurker:
    """
    Blocks this thread.
    """

    handlers = startup.load_handlers()
    dispatcher = ActionDispatcher(handlers, startup.config.LURKER_OUTPUT_DEVICE)

    model_path = _resolve_speech_model(
        startup.lurker_home,
        startup.config.LURKER_LANGUAGE,
        startup.config.LURKER_SPEECH_MODEL_SUFFIX,
    )
    keyword = Keyword(startup.config.LURKER_KEYWORD)

    transcriber = Transcriber(keyword=keyword, model_dir_path=model_path)
    listener = SpeechToTextListener(
        transcriber=transcriber,
        instruction_callback=dispatcher.act_on_instruction,
        input_device_name=startup.config.LURKER_INPUT_DEVICE,
        output_device_name=startup.config.LURKER_OUTPUT_DEVICE,
        speech_config=startup.config.LURKER_SPEECH_CONFIG,
    )

    return Lurker(listener=listener, output_device_name=startup.config.LURKER_OUTPUT_DEVICE)
