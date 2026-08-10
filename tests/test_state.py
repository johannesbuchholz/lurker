import pytest

from src.handlers.lights import State


class TestStateBounds:
    def test_empty_state_is_valid(self) -> None:
        State()

    def test_zero_percentages_are_valid(self) -> None:
        State(on=True, hue=0, sat=0, bri=0)

    def test_upper_bounds_are_valid(self) -> None:
        State(on=True, hue=360, sat=100, bri=100)

    @pytest.mark.parametrize("hue", [361, -1, 400])
    def test_hue_out_of_range(self, hue: int) -> None:
        with pytest.raises(ValueError):
            State(hue=hue)

    @pytest.mark.parametrize("sat", [101, -1])
    def test_sat_out_of_range(self, sat: int) -> None:
        with pytest.raises(ValueError):
            State(sat=sat)

    @pytest.mark.parametrize("bri", [101, -1])
    def test_bri_out_of_range(self, bri: int) -> None:
        with pytest.raises(ValueError):
            State(bri=bri)

    def test_on_must_be_bool(self) -> None:
        with pytest.raises(TypeError):
            State(on="yes")


class TestStateDict:
    def test_omits_none_values(self) -> None:
        assert State(on=False).to_dict() == {"on": False}

    def test_includes_all_present_values(self) -> None:
        state = State(on=True, hue=180, sat=50, bri=75)
        assert state.to_dict() == {"on": True, "hue": 180, "sat": 50, "bri": 75}
