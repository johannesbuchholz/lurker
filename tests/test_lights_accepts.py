import pytest

import lights
from lights import handler as handler_module
from lights.dummy import DummyBackend
from lights.handler import LightsHandler
from lights.hue import HueBackend
from lights.light import Light, State
from lights.noop import NoopBackend
from src.action_handler import LurkerContext


def _context() -> LurkerContext:
    return LurkerContext(
        lurker_home="/tmp/lurker-home",
        plugin_root_dir="/tmp/lurker-home/plugins",
        log_level="INFO",
        language="en",
    )


class StubBackend:
    def __init__(self) -> None:
        self.applied: list[list[Light]] = []
        self._state = {"1": Light(id="1", name="Kitchen", state=State(on=True))}

    def get_state(self) -> dict[str, Light]:
        return self._state

    def apply(self, lights) -> int:
        self.applied.append(list(lights))
        return 7


class StubGenerator:
    def __init__(self, result: list[Light]) -> None:
        self.result = result
        self.calls: list[tuple[str, dict]] = []

    def generate_lights(self, instruction: str, state: dict) -> list[Light]:
        self.calls.append((instruction, state))
        return self.result


@pytest.mark.parametrize(
    "instruction",
    [
        "turn on the light",
        "turn off the lights",
        "dim the desk lamp",
        "all lamps on",
        "mach das licht an",
        "die lichter aus",
        "schalte die lampe ein",
        "alle lampen aus",
    ],
)
def test_accepts_light_instructions(instruction: str) -> None:
    assert LightsHandler(_context(), {}).accepts(instruction)


@pytest.mark.parametrize(
    "instruction",
    [
        "what time is it",
        "play some music",
        "how is the weather",
    ],
)
def test_rejects_non_light_instructions(instruction: str) -> None:
    assert not LightsHandler(_context(), {}).accepts(instruction)


def test_handle_returns_one_without_lights() -> None:
    backend = StubBackend()
    generator = StubGenerator([])
    handler = LightsHandler(_context(), {}, backend=backend, generator=generator)

    assert handler.handle("turn on the light") == 1
    assert backend.applied == []
    assert generator.calls == [("turn on the light", backend.get_state())]


def test_handle_applies_generated_lights() -> None:
    light = Light(id="1", name="Kitchen", state=State(on=True))
    backend = StubBackend()
    generator = StubGenerator([light])
    handler = LightsHandler(_context(), {}, backend=backend, generator=generator)

    assert handler.handle("turn on the light") == 7
    assert backend.applied == [[light]]


def test_noop_backend_handles_without_generator() -> None:
    class FailingGenerator:
        def generate_lights(self, instruction, state):
            raise AssertionError("generator must not be used for noop")

    handler = LightsHandler(_context(), {"backend": "noop"}, generator=FailingGenerator())

    assert handler.handle("turn on the light") == 0


def test_default_backend_is_dummy() -> None:
    handler = LightsHandler(_context(), {})

    assert isinstance(handler._backend, DummyBackend)


def test_noop_backend_from_config() -> None:
    handler = LightsHandler(_context(), {"backend": "noop"})

    assert isinstance(handler._backend, NoopBackend)


def test_hue_backend_from_config() -> None:
    handler = LightsHandler(_context(), {"backend": "hue", "host": "bridge", "user": "user"})

    assert isinstance(handler._backend, HueBackend)
    assert handler._backend.host == "bridge"
    assert handler._backend.user == "user"


@pytest.mark.parametrize(
    "config",
    [
        {"backend": "hue"},
        {"backend": "hue", "host": "bridge"},
        {"backend": "hue", "user": "user"},
        {"backend": "unknown"},
    ],
)
def test_invalid_backend_config_raises(config: dict) -> None:
    with pytest.raises(ValueError):
        LightsHandler(_context(), config)


def test_construction_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise AssertionError("constructor must not touch resources, network or ONNX")

    monkeypatch.setattr(handler_module, "resolve_embedding_model_path", fail)
    monkeypatch.setattr(handler_module, "ActionGenerator", fail)

    LightsHandler(_context(), {})
    LightsHandler(_context(), {"backend": "noop"})
    LightsHandler(_context(), {"backend": "hue", "host": "bridge", "user": "user"})


@pytest.mark.parametrize("config", [{}, {"backend": "hue", "host": "bridge", "user": "user"}])
def test_ensure_resources_ensures_embedding_model(monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    calls: list[str] = []

    def fake_resolve(lurker_home: str) -> str:
        calls.append(lurker_home)
        return f"{lurker_home}/model"

    monkeypatch.setattr(handler_module, "resolve_embedding_model_path", fake_resolve)

    LightsHandler(_context(), config).ensure_resources()

    assert calls == ["/tmp/lurker-home"]


def test_ensure_resources_is_a_noop_for_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(lurker_home: str) -> str:
        raise AssertionError("noop must not ensure resources")

    monkeypatch.setattr(handler_module, "resolve_embedding_model_path", fail)

    LightsHandler(_context(), {"backend": "noop"}).ensure_resources()


def test_package_exposes_handler() -> None:
    assert lights.Handler is LightsHandler
