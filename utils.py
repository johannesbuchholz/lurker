from threading import Thread


class BackgroundExitCondition:
    """
    Used to start a background thread listening until some condition is met that eventually changes internal state of
    this class. This state might be queried by other processes to check if that condition has been met.
    """

    def __init__(self):
        self._is_exit_condition_met = False
        self._background_thread = Thread(target=self._wait_for_user_input, name="BackgroundExitCondition-Thread", daemon=True)

    def start_evaluating_in_background(self) -> None:
        self._background_thread.start()

    def _wait_for_user_input(self) -> None:
        input()
        self._is_exit_condition_met = True

    def is_met(self) -> bool:
        return self._is_exit_condition_met
