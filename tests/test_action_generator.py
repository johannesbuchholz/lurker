from pathlib import Path

import pytest

from src.actions.action import ActionGenerator, _extract_room
from src.actions.models import SCENES
from src.handlers.lights import Light, State
from src.lurker import _resolve_embedding_model_path

MODEL_PATH = _resolve_embedding_model_path(str(Path(__file__).resolve().parents[1] / "lurker"))

LIGHT_NAMES = [
    "Living Room Entry",
    "Living Room Couch",
    "Living Room Ceiling",
    "Living Room Table",
    "Living Room Desk",
    "Kitchen",
    "Floor 1",
    "Floor 2",
    "Bedroom Ceiling",
    "Bedroom Nightstand Alex",
    "Bedroom Nightstand Jenny",
]


def _initial_state() -> dict[str, Light]:
    return {
        str(i): Light(id=str(i), name=name, state=State(on=True, bri=50))
        for i, name in enumerate(LIGHT_NAMES, start=1)
    }


@pytest.fixture(scope="module")
def generator() -> ActionGenerator:
    return ActionGenerator(model_path=MODEL_PATH, initial_state=_initial_state())


class TestExtractRoom:
    def test_kitchen(self) -> None:
        is_restricted, lights = _extract_room("turn the kitchen light off", LIGHT_NAMES)
        assert is_restricted
        assert lights == ["Kitchen"]

    def test_table(self) -> None:
        is_restricted, lights = _extract_room("dim the table light", LIGHT_NAMES)
        assert is_restricted
        assert lights == ["Living Room Table"]

    def test_room(self) -> None:
        is_restricted, lights = _extract_room("all lights on in the living room", LIGHT_NAMES)
        assert is_restricted
        assert lights == [name for name in LIGHT_NAMES if name.startswith("Living Room")]

    def test_unrelated_returns_nothing(self) -> None:
        is_restricted, lights = _extract_room("what time is it", LIGHT_NAMES)
        assert not is_restricted
        assert lights == []


class TestGuessLights:
    def test_all_lights(self, generator: ActionGenerator) -> None:
        assert set(generator.guess_lights("Turn all lights off", LIGHT_NAMES)) == set(LIGHT_NAMES)

    def test_token_match(self, generator: ActionGenerator) -> None:
        assert "Kitchen" in generator.guess_lights("Turn the kitchen light off", LIGHT_NAMES)

    def test_unrelated_rejected(self, generator: ActionGenerator) -> None:
        assert generator.guess_lights("What time is it", LIGHT_NAMES) == []

    def test_generate_lights_off(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Turn the kitchen light off", _initial_state())
        assert len(actions) == 1
        assert actions[0].light_ids == ["6"]
        assert actions[0].state == State(on=False)

    def test_generic_command_targets_all_lights(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Dim the light", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)

    def test_scene_targets_all_lights(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Movie night", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)
        assert all(action.state == SCENES[0].state for action in actions)


class TestEndToEnd:
    def test_brighten_all(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Make it brighter", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)
        assert all(a.state == State(on=True, bri=75) for a in actions)

    def test_blue_all(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Make the light blue", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)
        assert all(a.state == State(on=True, hue=240, sat=100, bri=70) for a in actions)

    def test_on_all(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Turn the lights on", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)
        assert all(a.state == State(on=True) for a in actions)

    def test_movie_phrase_rejected(self, generator: ActionGenerator) -> None:
        assert generator.generate_lights("That movie was great", _initial_state()) == []

    def test_warm_all(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Make it warm", _initial_state())
        assert len(actions) == len(LIGHT_NAMES)
        assert all(a.state == State(on=True, hue=25, sat=70, bri=70) for a in actions)

    def test_bedside_lamp(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("turn on the bedside lamp", _initial_state())
        assert {a.light_ids[0] for a in actions} == {"9", "10", "11"}
        assert all(a.state == State(on=True) for a in actions)

    def test_cozy_reading_light(self, generator: ActionGenerator) -> None:
        actions = generator.generate_lights("Cozy reading light", _initial_state())
        assert {a.light_ids[0] for a in actions} == {"10", "11"}
        assert all(a.state == SCENES[4].state for a in actions)

    def test_unrelated_noop(self, generator: ActionGenerator) -> None:
        assert generator.generate_lights("What time is it", _initial_state()) == []
