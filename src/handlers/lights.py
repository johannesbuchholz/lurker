import json
from dataclasses import dataclass
from typing import Collection


@dataclass(frozen=True, slots=True)
class State:
    ALLOWED_LIGHT_KEYS = ["on", "sat", "bri", "hue"]

    on: bool | None = None
    hue: int | None = None
    sat: int | None = None
    bri: int | None = None

    def __post_init__(self):
        if self.hue is not None and not 0 <= self.hue <= 360:
            raise ValueError(f"hue out of range [0, 360]: {self.hue}")
        if self.sat is not None and not 0 <= self.sat <= 100:
            raise ValueError(f"sat out of range [0, 100]: {self.sat}")
        if self.bri is not None and not 0 <= self.bri <= 100:
            raise ValueError(f"bri out of range [0, 100]: {self.bri}")
        if self.on is not None and not isinstance(self.on, bool):
            raise TypeError(f"on must be a bool, got {type(self.on).__name__}: {self.on!r}")

    def __str__(self):
        return str(self.to_dict())

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict[str, bool | int]:
        return {k: v for k, v in {"on": self.on, "hue": self.hue, "sat": self.sat, "bri": self.bri}.items() if v is not None}


@dataclass(frozen=True, slots=True)
class Light:
    id: str
    name: str
    state: State

    def __str__(self):
        return f"{self.name} ({self.id}): {self.state}"


class LightAction:

    def __init__(self, light_ids: Collection[str], state: State):
        self.light_ids = light_ids
        self.state = state

    def __str__(self):
        return f"{self.__class__.__name__}[ids={self.light_ids}, state={self.state}]"

    def __repr__(self):
        return self.__str__()

def actions_from_json(json_str: str) -> list[LightAction]:
    data = json.loads(json_str)
    actions = []
    for light_ids_str, state_dict in data.items():
        state = State(**state_dict)
        action = LightAction(light_ids_str, state)
        actions.append(action)
    return actions
