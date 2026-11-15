from collections.abc import Sequence

from src import log, sound
from src.action_handler import ActionHandler


class ActionDispatcher:
    def __init__(self, handlers: Sequence[ActionHandler], output_device_name: str | None) -> None:
        self._handlers = list(handlers)
        self._output_device_name = output_device_name
        self._logger = log.new_logger(type(self).__name__)

    def act_on_instruction(self, instruction: str) -> None:
        self._logger.debug(f"Trying to find action for instruction '{instruction}'")
        sound.play_understood(self._output_device_name)

        accepting_handlers: list[ActionHandler] = []
        for handler in self._handlers:
            try:
                if handler.accepts(instruction):
                    accepting_handlers.append(handler)
            except Exception as error:
                self._logger.error(
                    f"Handler {handler.key} failed to accept instruction: {type(error)} {error}",
                    exc_info=error,
                )

        if not accepting_handlers:
            self._logger.info(f"No handler accepted instruction '{instruction}'")
            sound.play_no(self._output_device_name)
            return

        exit_codes: list[int] = []
        for handler in accepting_handlers:
            try:
                exit_code = handler.handle(instruction)
            except Exception as error:
                self._logger.error(
                    f"Handler {handler.key} failed to handle instruction: {type(error)} {error}",
                    exc_info=error,
                )
                exit_code = 1
            exit_codes.append(exit_code)

        if all(exit_code == 0 for exit_code in exit_codes):
            self._logger.info(f"Successfully acted on instruction: {instruction}")
            sound.play_ok(self._output_device_name)
        else:
            self._logger.info(
                f"Could not act on instruction: instruction={instruction}, "
                f"exit_codes={exit_codes}"
            )
            sound.play_no(self._output_device_name)
