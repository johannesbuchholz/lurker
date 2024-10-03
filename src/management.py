from src import log, sound
from src.action import ActionRegistry, ActionHandler

LOGGER = log.new_logger(__name__)

class Orchestrator:
    """
    Ties different services together in order to act upon incoming instructions.
    """

    def __init__(self, registry: ActionRegistry, handler: ActionHandler, output_device_name: str = None):
        self.registry = registry
        self.handler = handler
        self.output_device_name = output_device_name


    def act(self, instruction: str) -> None:
        action = self.registry.find(instruction)
        if action is None:
            LOGGER.info("Could not find action for instruction '%s'", instruction)
            sound.play_positive(self.output_device_name)
        else:
            LOGGER.debug("Found action %s", action, instruction)
            is_success = self.handler.handle(action)
            if is_success:
                LOGGER.info("Successfully acted on instruction: %s", instruction)
                sound.play_positive(self.output_device_name)
            else:
                LOGGER.info("Could not act on instruction: %s", instruction)
                sound.play_negative(self.output_device_name)
