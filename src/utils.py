from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Action:

    type: str
    """The type of this action. Handlers may decide to accept or reject an action based on this type."""
    payload: dict[str, Any]
    """The payload of the action. May be deserialized into a proper object."""

