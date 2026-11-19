import subprocess

import pytest
import shutdown
from shutdown import handler as handler_module
from shutdown.handler import ShutdownHandler

from src.action_handler import LurkerContext


def _context() -> LurkerContext:
    return LurkerContext(
        lurker_home="/tmp/lurker-home",
        plugin_root_dir="/tmp/lurker-home/plugins",
        log_level="INFO",
        language="en",
    )


@pytest.mark.parametrize(
    "instruction",
    [
        "lorem ipsum",
        "please lorem ipsum now",
        "LOREM IPSUM",
    ],
)
def test_accepts_trigger(instruction: str) -> None:
    assert ShutdownHandler(_context(), {}).accepts(instruction)


@pytest.mark.parametrize(
    "instruction",
    [
        "what time is it",
        "turn on the light",
        "lorem",
        "ipsum",
    ],
)
def test_rejects_non_trigger(instruction: str) -> None:
    assert not ShutdownHandler(_context(), {}).accepts(instruction)


def test_trigger_is_configurable() -> None:
    handler = ShutdownHandler(_context(), {"trigger": "power off"})

    assert handler.accepts("please POWER OFF the machine")
    assert not handler.accepts("lorem ipsum")


def test_empty_trigger_falls_back_to_default() -> None:
    handler = ShutdownHandler(_context(), {"trigger": "   "})

    assert handler.accepts("lorem ipsum")


def test_handle_schedules_delayed_background_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict]] = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return object()

    monkeypatch.setattr(handler_module.subprocess, "Popen", fake_popen)

    assert ShutdownHandler(_context(), {}).handle("please lorem ipsum") == 0
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == ["/bin/sh", "-c", "sleep 3; exec poweroff"]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL


def test_handle_returns_one_when_shutdown_cannot_be_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_popen(command, **kwargs):
        raise OSError("shutdown")

    monkeypatch.setattr(handler_module.subprocess, "Popen", fake_popen)

    assert ShutdownHandler(_context(), {}).handle("please lorem ipsum") == 1


def test_package_exposes_handler() -> None:
    assert shutdown.Handler is ShutdownHandler
