import subprocess

from src.action_handler import ActionHandler, LurkerContext

DEFAULT_TRIGGER = "lorem ipsum"


class ShutdownHandler(ActionHandler):
    key = "shutdown"

    def __init__(self, context: LurkerContext, config: dict) -> None:
        super().__init__(context, config)
        self._trigger = str(config.get("trigger", DEFAULT_TRIGGER)).strip().lower()
        if not self._trigger:
            self._trigger = DEFAULT_TRIGGER

    def accepts(self, instruction: str) -> bool:
        trigger = self.config.get("trigger", "").__str__().lower()
        if not trigger:
            return False
        else:
            return trigger in instruction.strip().lower()

    def handle(self, instruction: str) -> int:
        delay_seconds = self.config.get("delay", "3").__str__()
        delay_seconds = max(0, int(delay_seconds))
        self._logger.info(f"Powering off the machine in {delay_seconds} seconds for instruction '{instruction}'")
        try:
            subprocess.Popen(
                ["/bin/sh", "-c", f"sleep {delay_seconds}; exec poweroff"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as error:
            self._logger.error(f"Could not schedule poweroff: {type(error)} {error}")
            return 1
        return 0
