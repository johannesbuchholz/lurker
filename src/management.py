from src import log, sound
from src.action import ActionRegistry, ActionHandler


class Orchestrator:
    """
    Ties different services together in order to act upon incoming instructions.
    """

    def __init__(self, registry: ActionRegistry, handler: ActionHandler, output_device_name: str = None):
        self._logger = log.new_logger(self.__class__.  __name__)
        self.registry = registry
        self.handler = handler
        self.output_device_name = output_device_name

    # TODO: Add another sound in order to distinguish between successfully finding an action and successfully handling on an action.
    def act(self, instruction: str) -> None:
        action = self.registry.find(instruction)
        if action is None:
            self._logger.info(f"Could not find action for instruction '{instruction}'")
            sound.play_negative(self.output_device_name)
        else:
            self._logger.debug(f"Found action for instruction {instruction}: {action}")
            sound.play_positive(self.output_device_name)
            is_success = self.handler.handle(action)
            if is_success:
                self._logger.info(f"Successfully acted on instruction: {instruction}")
            else:
                self._logger.info(f"Could not act on instruction: {instruction}")
