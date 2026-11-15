from collections.abc import Collection

from src import log
from .light import Light, State

_DUMMY_LIGHTS_EN: dict[str, Light] = {
    "1": Light(id="1", name="Living Room Lamp", state=State(on=True, bri=50, hue=44, sat=79)),
    "2": Light(id="2", name="Desk Lamp", state=State(on=True, bri=100, hue=220, sat=39)),
    "3": Light(id="3", name="Bedroom Light", state=State(on=False, bri=0, hue=0, sat=0)),
    "4": Light(id="4", name="Living Room Entry", state=State(on=True, bri=50, hue=44, sat=79)),
    "5": Light(id="5", name="Living Room Couch", state=State(on=True, bri=79, hue=192, sat=59)),
    "6": Light(id="6", name="Living Room Ceiling", state=State(on=True, bri=100, hue=220, sat=39)),
    "7": Light(id="7", name="Living Room Table", state=State(on=True, bri=35, hue=55, sat=71)),
    "8": Light(id="8", name="Living Room Desk", state=State(on=False, bri=0, hue=0, sat=0)),
    "9": Light(id="9", name="Kitchen", state=State(on=True, bri=59, hue=27, sat=87)),
    "10": Light(id="10", name="Floor 1", state=State(on=True, bri=39, hue=165, sat=51)),
    "11": Light(id="11", name="Floor 2", state=State(on=True, bri=30, hue=110, sat=63)),
    "12": Light(id="12", name="Bedroom Ceiling", state=State(on=False, bri=0, hue=0, sat=0)),
    "13": Light(id="13", name="Bedroom Nightstand Alex", state=State(on=True, bri=71, hue=66, sat=35)),
    "14": Light(id="14", name="Bedroom Nightstand Jenny", state=State(on=True, bri=87, hue=247, sat=47)),
}

_DUMMY_LIGHTS_DE: dict[str, Light] = {
    "1": Light(id="1", name="Wohnzimmer Lampe", state=State(on=True, bri=50, hue=44, sat=79)),
    "2": Light(id="2", name="Schreibtisch Lampe", state=State(on=True, bri=100, hue=220, sat=39)),
    "3": Light(id="3", name="Schlafzimmer Licht", state=State(on=False, bri=0, hue=0, sat=0)),
    "4": Light(id="4", name="Wohnzimmer Eingang", state=State(on=True, bri=50, hue=44, sat=79)),
    "5": Light(id="5", name="Wohnzimmer Couch", state=State(on=True, bri=79, hue=192, sat=59)),
    "6": Light(id="6", name="Wohnzimmer Decke", state=State(on=True, bri=100, hue=220, sat=39)),
    "7": Light(id="7", name="Wohnzimmer Tisch", state=State(on=True, bri=35, hue=55, sat=71)),
    "8": Light(id="8", name="Wohnzimmer Schreibtisch", state=State(on=False, bri=0, hue=0, sat=0)),
    "9": Light(id="9", name="Küche", state=State(on=True, bri=59, hue=27, sat=87)),
    "10": Light(id="10", name="Etage 1", state=State(on=True, bri=39, hue=165, sat=51)),
    "11": Light(id="11", name="Etage 2", state=State(on=True, bri=30, hue=110, sat=63)),
    "12": Light(id="12", name="Schlafzimmer Decke", state=State(on=False, bri=0, hue=0, sat=0)),
    "13": Light(id="13", name="Schlafzimmer Nachttisch Alex", state=State(on=True, bri=71, hue=66, sat=35)),
    "14": Light(id="14", name="Schlafzimmer Nachttisch Jenny", state=State(on=True, bri=87, hue=247, sat=47)),
}


class DummyBackend:
    """Returns a fixed example light state and logs actions without executing them."""

    def __init__(self, language: str = "en"):
        self._language = language
        self._logger = log.new_logger(type(self).__name__)

    def get_state(self) -> dict[str, Light]:
        if self._language == "de":
            return dict(_DUMMY_LIGHTS_DE)
        return dict(_DUMMY_LIGHTS_EN)

    def apply(self, lights: Collection[Light]) -> int:
        self._logger.info(f"Logging action without executing it: {lights}")
        return 0
