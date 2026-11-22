import numpy as np
import pytest

from lights.intents import (
    COLOR_PATTERNS,
    guess_intent_and_apply,
    apply_intent_individual,
    apply_intent_off,
    apply_intent_scene,
)
from lights.light import Light, State
from lights.models import SCENES


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

    @pytest.mark.parametrize(
        "instruction",
        [
            "Turn the kitchen light to 60 percent",
            "Set the brightness to 60 %",
            "Dim the light to 60%",
            "Dim the light to 60 percent",
            "Dim the light to sixty percent",
            "Dimme das Licht auf 60 Prozent",
            "Dimme das Licht auf sechzig Prozent",
            "Schalte das Licht auf 60 %",
            "Stelle die Helligkeit auf 60 %",
            "Helligkeit auf 60 Prozent",
        ],
    )
    def test_dim_absolute(self, instruction: str) -> None:
        result = apply_intent_individual(instruction, AFFECTED)
        assert _states(result) == [{"on": True, "bri": 60}, {"on": True, "bri": 60}]

    @pytest.mark.parametrize(
        ("instruction", "bri"),
        [
            ("Dim the light to sixty-five percent", 65),
            ("Turn the light to twenty five percent", 25),
            ("Turn the light to zero percent", 0),
            ("Turn the light to one hundred percent", 100),
            ("Dimme das Licht auf fünfundzwanzig Prozent", 25),
            ("Schalte das Licht auf null Prozent", 0),
        ],
    )
    def test_dim_absolute_number_words(self, instruction: str, bri: int) -> None:
        result = apply_intent_individual(instruction, AFFECTED)
        assert _states(result) == [{"on": bri > 0, "bri": bri}, {"on": bri > 0, "bri": bri}]

    def test_dim_absolute_clamps_to_100(self) -> None:
        result = apply_intent_individual("Turn the light to 150%", AFFECTED)
        assert _states(result) == [{"on": True, "bri": 100}, {"on": True, "bri": 100}]

    def test_dim_absolute_zero_turns_off(self) -> None:
        result = apply_intent_individual("Turn the light to 0%", AFFECTED)
        assert _states(result) == [{"on": False, "bri": 0}, {"on": False, "bri": 0}]

    def test_percent_without_dim_context_is_ignored(self) -> None:
        assert apply_intent_individual("The battery is at 70%", AFFECTED) is None

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
        result = guess_intent_and_apply("Turn off the movie lights", AFFECTED, EMBEDDER)
        assert _states(result) == [{"on": False}, {"on": False}]

    def test_scene(self) -> None:
        result = guess_intent_and_apply("Movie night", AFFECTED, EMBEDDER)
        assert result is not None
        assert result[0].state == SCENES[0].state

    def test_individual(self) -> None:
        result = guess_intent_and_apply("Dim the light", AFFECTED, EMBEDDER)
        assert _states(result) == [{"on": True, "bri": 40}, {"on": True, "bri": 20}]

    def test_absolute_brightness(self) -> None:
        result = guess_intent_and_apply("Turn the light to 60 percent", AFFECTED, EMBEDDER)
        assert _states(result) == [{"on": True, "bri": 60}, {"on": True, "bri": 60}]

    def test_no_match_returns_none(self) -> None:
        assert guess_intent_and_apply("What time is it", AFFECTED, EMBEDDER) is None
