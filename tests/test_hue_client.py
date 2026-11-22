import json

import pytest

from lights import hue as hue_module
from lights.dummy import DummyBackend
from lights.hue import (
    HueBackend,
    _from_api_state,
    _map_to_lights,
    _to_api_state,
)
from lights.light import Light, State
from tests.test_action_generator import LIGHT_NAMES

DUMMY_RESPONSE_JSON: dict = json.loads("""
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
  },
  "4": {
    "state": { "on": true, "bri": 128, "hue": 8000, "sat": 200 },
    "name": "Living Room Entry",
    "type": "Extended color light"
  },
  "5": {
    "state": { "on": true, "bri": 200, "hue": 35000, "sat": 150 },
    "name": "Living Room Couch",
    "type": "Extended color light"
  },
  "6": {
    "state": { "on": true, "bri": 254, "hue": 40000, "sat": 100 },
    "name": "Living Room Ceiling",
    "type": "Extended color light"
  },
  "7": {
    "state": { "on": true, "bri": 90, "hue": 10000, "sat": 180 },
    "name": "Living Room Table",
    "type": "Extended color light"
  },
  "8": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Living Room Desk",
    "type": "Extended color light"
  },
  "9": {
    "state": { "on": true, "bri": 150, "hue": 5000, "sat": 220 },
    "name": "Kitchen",
    "type": "Extended color light"
  },
  "10": {
    "state": { "on": true, "bri": 100, "hue": 30000, "sat": 130 },
    "name": "Floor 1",
    "type": "Extended color light"
  },
  "11": {
    "state": { "on": true, "bri": 75, "hue": 20000, "sat": 160 },
    "name": "Floor 2",
    "type": "Extended color light"
  },
  "12": {
    "state": { "on": false, "bri": 0, "hue": 0, "sat": 0 },
    "name": "Bedroom Ceiling",
    "type": "Extended color light"
  },
  "13": {
    "state": { "on": true, "bri": 180, "hue": 12000, "sat": 90 },
    "name": "Bedroom Nightstand Alex",
    "type": "Extended color light"
  },
  "14": {
    "state": { "on": true, "bri": 220, "hue": 45000, "sat": 120 },
    "name": "Bedroom Nightstand Jenny",
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
        assert set(lights) == DUMMY_RESPONSE_JSON.keys()
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


class TestDummyBackend:
    def test_get_state_contains_all_light_names(self) -> None:
        state = DummyBackend().get_state()
        assert set(LIGHT_NAMES) <= {light.name for light in state.values()}

    def test_apply_logs_and_succeeds(self) -> None:
        assert DummyBackend().apply([]) == 0

    def test_apply_updates_reported_state(self) -> None:
        backend = DummyBackend()

        assert backend.apply([Light(id="1", name="Living Room Lamp", state=State(on=True, bri=25))]) == 0
        assert backend.get_state()["1"].state == State(on=True, bri=25, hue=44, sat=79)

    def test_apply_merges_partial_state(self) -> None:
        backend = DummyBackend()

        backend.apply([Light(id="2", name="Desk Lamp", state=State(on=False))])

        assert backend.get_state()["2"].state == State(on=False, bri=100, hue=220, sat=39)

    def test_instances_keep_independent_state(self) -> None:
        first, second = DummyBackend(), DummyBackend()

        first.apply([Light(id="1", name="Living Room Lamp", state=State(on=False))])

        assert first.get_state()["1"].state.on is False
        assert second.get_state()["1"].state.on is True

    def test_german_backend_updates_german_lights(self) -> None:
        backend = DummyBackend(language="de")

        backend.apply([Light(id="1", name="Wohnzimmer Lampe", state=State(bri=20))])

        state = backend.get_state()["1"]
        assert state.name == "Wohnzimmer Lampe"
        assert state.state == State(on=True, bri=20, hue=44, sat=79)


KITCHEN = Light(id="1", name="Kitchen", state=State(on=False))
DESK = Light(id="2", name="Desk Lamp", state=State(on=True, bri=100))
KITCHEN_URL = "http://bridge/api/user/lights/1/state"
DESK_URL = "http://bridge/api/user/lights/2/state"
KITCHEN_REQUEST = {KITCHEN_URL: {"on": False}}
BOTH_REQUESTS = {KITCHEN_URL: {"on": False}, DESK_URL: {"on": True, "bri": 254}}


class TestApply:
    """apply() sends one request per light in the collection."""
    @pytest.fixture
    def backend(self) -> HueBackend:
        backend = HueBackend(host="bridge", user="user")
        backend.lights = {"1": {"name": "Kitchen", "state": {"on": True}}}
        return backend

    @pytest.fixture
    def dispatched(self, monkeypatch: pytest.MonkeyPatch) -> list:
        dispatched: list = []
        monkeypatch.setattr(hue_module, "urlopen", lambda request, timeout: dispatched.append(request))
        return dispatched

    @pytest.mark.parametrize(("lights", "expected_requests"), [
        ([KITCHEN], KITCHEN_REQUEST),
        ([KITCHEN, DESK], BOTH_REQUESTS),
        ((KITCHEN, DESK), BOTH_REQUESTS),
        ({KITCHEN, DESK}, BOTH_REQUESTS),
        ([], {}),
        ((), {}),
    ])
    def test_apply_dispatches_lights(self, backend: HueBackend, dispatched: list, lights, expected_requests) -> None:
        assert backend.apply(lights) == 0
        assert {request.full_url: json.loads(request.data) for request in dispatched} == expected_requests
