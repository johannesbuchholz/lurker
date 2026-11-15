from collections.abc import Collection

from .light import Light


class NoopBackend:
    def get_state(self) -> dict[str, Light]:
        return {}

    def apply(self, lights: Collection[Light]) -> int:
        return 0
