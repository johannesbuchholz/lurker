from src import dispatch as dispatch_module
from src.action_handler import ActionHandler, LurkerContext
from src.dispatch import ActionDispatcher


class StubHandler(ActionHandler):
    def __init__(self, *, accepts: bool = True, exit_code: int = 0, name: str = "stub"):
        self.context = None
        self.key = name
        self._accepts = accepts
        self._exit_code = exit_code
        self.accepted: list[str] = []
        self.handled: list[str] = []

    def accepts(self, instruction: str) -> bool:
        self.accepted.append(instruction)
        return self._accepts

    def handle(self, instruction: str) -> int:
        self.handled.append(instruction)
        return self._exit_code


class RaisingAcceptHandler(StubHandler):
    def accepts(self, instruction: str) -> bool:
        raise RuntimeError("accept failed")


class RaisingHandleHandler(StubHandler):
    def handle(self, instruction: str) -> int:
        self.handled.append(instruction)
        raise RuntimeError("handle failed")


class SoundRecorder:
    def __init__(self, events: list[str]):
        self._events = events

    def play_understood(self, device):
        self._events.append("understood")

    def play_ok(self, device):
        self._events.append("ok")

    def play_no(self, device):
        self._events.append("no")


def _patch_sound(monkeypatch, events):
    recorder = SoundRecorder(events)
    monkeypatch.setattr(dispatch_module.sound, "play_understood", recorder.play_understood)
    monkeypatch.setattr(dispatch_module.sound, "play_ok", recorder.play_ok)
    monkeypatch.setattr(dispatch_module.sound, "play_no", recorder.play_no)
    return recorder


def test_only_accepting_handlers_are_called(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)
    accepting = StubHandler(accepts=True)
    rejecting = StubHandler(accepts=False)

    ActionDispatcher([accepting, rejecting], None).act_on_instruction("do it")

    assert accepting.handled == ["do it"]
    assert rejecting.handled == []
    assert events == ["understood", "ok"]


def test_no_accepting_handler_plays_no(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)
    rejecting = StubHandler(accepts=False)

    ActionDispatcher([rejecting], None).act_on_instruction("do it")

    assert rejecting.handled == []
    assert events == ["understood", "no"]


def test_all_accepting_handlers_are_called_and_ok_needs_all_successful(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)
    first = StubHandler(exit_code=0, name="first")
    second = StubHandler(exit_code=1, name="second")

    ActionDispatcher([first, second], None).act_on_instruction("do it")

    assert first.handled == ["do it"]
    assert second.handled == ["do it"]
    assert events == ["understood", "no"]


def test_all_successful_plays_ok(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)

    ActionDispatcher([StubHandler(), StubHandler()], None).act_on_instruction("do it")

    assert events == ["understood", "ok"]


def test_accept_exception_is_a_reject(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)
    failing = RaisingAcceptHandler()
    working = StubHandler()

    ActionDispatcher([failing, working], None).act_on_instruction("do it")

    assert failing.handled == []
    assert working.handled == ["do it"]
    assert events == ["understood", "ok"]


def test_handle_exception_is_exit_code_one(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)
    failing = RaisingHandleHandler()
    working = StubHandler()

    ActionDispatcher([failing, working], None).act_on_instruction("do it")

    assert failing.handled == ["do it"]
    assert working.handled == ["do it"]
    assert events == ["understood", "no"]


def test_understood_is_played_before_handling(monkeypatch):
    events = []
    _patch_sound(monkeypatch, events)

    class OrderHandler(StubHandler):
        def handle(self, instruction: str) -> int:
            events.append("handle")
            return 0

    ActionDispatcher([OrderHandler()], None).act_on_instruction("do it")

    assert events == ["understood", "handle", "ok"]
