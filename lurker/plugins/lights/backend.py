from collections.abc import Collection
from typing import Protocol

from .light import Light


class LightBackend(Protocol):
    def get_state(self) -> dict[str, Light]: ...

    def apply(self, lights: Collection[Light]) -> int: ...
