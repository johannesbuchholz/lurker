import numpy as np

from src.actions.intents import (
    COLOR_PATTERNS,
    apply_intent,
    apply_intent_individual,
    apply_intent_off,
    apply_intent_scene,
)
from src.actions.models import SCENES
from src.handlers.lights import Light, State


class ConstantEmbedder:
    def embed(self, text: str) -> np.ndarray:
        return np.array([1.0, 0.0, 0.0], dtype=np.float32)


EMBEDDER = ConstantEmbedder()

KITCHEN = Light(id="1", name="Kitchen", state=State(on=True, bri=80))
DESK = Light(id="2", name="Desk Lamp", state=State(on=True, bri=40))
AFFECTED = [KITCHEN, DESK]


def _states(result) -> list[dict]:
    return [light.state.to_dict() for light in result]


class TestApplyIntentOff:
    def test_off_query(self) -> None:
        result = apply_intent_off("Turn the kitchen light off", AFFECTED)
        assert _states(result) == [{"on": False}, {"on": False}]

    def test_non_off_query_returns_none(self) -> None:
        assert apply_intent_off("Make the light blue", AFFECTED) is None


class TestApplyIntentScene:
    def test_scene_applies_state_to_all(self) -> None:
        result = apply_intent_scene("Movie night", AFFECTED, SCENES, EMBEDDER)
        assert result is not None
        for light in result:
            assert light.state == SCENES[0].state

    def test_no_scene_keyword_returns_none(self) -> None:
        assert apply_intent_scene("Turn the lights on", AFFECTED, SCENES, EMBEDDER) is None

    def test_threshold_rejects(self) -> None:
        assert apply_intent_scene("Movie night", AFFECTED, SCENES, EMBEDDER, threshold=1.5) is None


class TestApplyIntentIndividual:
    def test_dim_down(self) -> None:
        result = apply_intent_individual("Dim the light", AFFECTED)
        assert _states(result) == [{"on": True, "bri": 40}, {"on": True, "bri": 20}]

    def test_dim_up(self) -> None:
        result = apply_intent_individual("Make it brighter", AFFECTED)
        assert _states(result) == [{"on": True, "bri": 100}, {"on": True, "bri": 60}]

    def test_dim_without_bri_falls_back_to_50(self) -> None:
        lights = [Light(id="1", name="Kitchen", state=State(on=True))]
        result = apply_intent_individual("Dim the light", lights)
        assert result[0].state.bri == 25

    def test_color(self) -> None:
        result = apply_intent_individual("Make the light blue", AFFECTED)
        assert _states(result) == [{"on": True, "hue": 240, "sat": 100, "bri": 70}] * 2

    def test_on(self) -> None:
        result = apply_intent_individual("Turn the lights on", AFFECTED)
        assert _states(result) == [{"on": True}, {"on": True}]

    def test_no_match_returns_none(self) -> None:
        assert apply_intent_individual("What time is it", AFFECTED) is None

    def test_empty_affected_returns_none(self) -> None:
        assert apply_intent_individual("Dim the light", []) is None

    def test_color_patterns_yield_valid_states(self) -> None:
        for _, state in COLOR_PATTERNS:
            assert state is not None


class TestApplyIntent:
    def test_off_wins_over_scene(self) -> None:
        result = apply_intent("Turn off the movie lights", AFFECTED, EMBEDDER)
        assert _states(result) == [{"on": False}, {"on": False}]

    def test_scene(self) -> None:
        result = apply_intent("Movie night", AFFECTED, EMBEDDER)
        assert result is not None
        assert result[0].state == SCENES[0].state

    def test_individual(self) -> None:
        result = apply_intent("Dim the light", AFFECTED, EMBEDDER)
        assert _states(result) == [{"on": True, "bri": 40}, {"on": True, "bri": 20}]

    def test_no_match_returns_none(self) -> None:
        assert apply_intent("What time is it", AFFECTED, EMBEDDER) is None
