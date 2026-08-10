import json

from src.handlers.hue_client import (
    _from_api_state,
    _map_to_lights,
    _to_api_state,
)
from src.handlers.lights import Light, State

DUMMY_RESPONSE_JSON = json.loads("""
{
  "1": {
    "state": { "on": true, "bri": 128, "hue": 8000, "sat": 200 },
    "name": "Living Room Lamp",
    "type": "Extended color light"
  },
  "2": {
    "state": { "on": true, "bri": 254, "hue": 40000, "sat": 100 },
    "name": "Desk Lamp",
    "type": "Extended color light"
  },
  "3": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Bedroom Light",
    "type": "Extended color light"
  }
}
""")


class TestFromApiState:
    def test_converts_hub_values_to_standard(self) -> None:
        api = {"on": True, "bri": 128, "hue": 8000, "sat": 200}
        state = _from_api_state(api)
        assert state == State(on=True, bri=50, hue=44, sat=79)

    def test_zero_hub_values_stay_valid(self) -> None:
        state = _from_api_state({"on": False, "bri": 0, "hue": 0, "sat": 0})
        assert state == State(on=False, bri=0, hue=0, sat=0)

    def test_absent_keys_stay_none(self) -> None:
        state = _from_api_state({"on": True})
        assert state == State(on=True)


class TestToApiState:
    def test_converts_standard_to_hub_values(self) -> None:
        api = _to_api_state(State(on=True, hue=180, sat=50, bri=100))
        assert api == {"on": True, "hue": 32768, "sat": 127, "bri": 254}

    def test_bri_zero_is_clamped_to_one(self) -> None:
        assert _to_api_state(State(on=True, bri=0)) == {"on": True, "bri": 1}

    def test_omits_none_values(self) -> None:
        assert _to_api_state(State(on=False)) == {"on": False}


class TestRoundTrip:
    def test_api_standard_api(self) -> None:
        original = {"on": True, "hue": 0, "sat": 127, "bri": 254}
        restored = _to_api_state(_from_api_state(original))
        assert restored == original


class TestMapToLights:
    def test_maps_dummy_response(self) -> None:
        lights = _map_to_lights(DUMMY_RESPONSE_JSON)
        assert set(lights) == {"1", "2", "3"}
        assert isinstance(lights["1"], Light)
        assert lights["1"].name == "Living Room Lamp"
        assert lights["1"].state == _from_api_state(DUMMY_RESPONSE_JSON["1"]["state"])

    def test_skips_entries_without_name_or_state(self) -> None:
        raw = {"1": {"name": "Kitchen", "state": {"on": True}}, "2": {"state": {"on": True}}, "3": {"name": "Desk"}}
        lights = _map_to_lights(raw)
        assert set(lights) == {"1"}
        assert lights["1"].name == "Kitchen"
        assert lights["1"].state == State(on=True)


class TestDummyResponseRoundTrip:
    def test_mapped_lights_roundtrip_through_standard_values(self) -> None:
        for light in _map_to_lights(DUMMY_RESPONSE_JSON).values():
            assert _from_api_state(_to_api_state(light.state)) == light.state
