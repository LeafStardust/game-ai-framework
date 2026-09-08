from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveBalatroSnapshot:
    sequence: int
    phase: str
    state_complete: bool
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LiveBalatroCommand:
    sequence: int
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
