"""Canonical public-state frame and episode ownership semantics for Phase R."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from games.balatro.state import BalatroState


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    ANTE_8_WIN = "ANTE_8_WIN"
    LOSS = "LOSS"

    @property
    def terminal(self) -> bool:
        return self is not RunStatus.RUNNING


class TurnOwner(str, Enum):
    AGENT = "AGENT"
    TACTICAL_POLICY = "TACTICAL_POLICY"
    ENVIRONMENT = "ENVIRONMENT"
    TERMINAL = "TERMINAL"


@dataclass(frozen=True)
class EnvStateFrame:
    """R0 wrapper around the existing canonical public ``BalatroState``."""

    state: BalatroState
    status: RunStatus = RunStatus.RUNNING
    owner: TurnOwner = TurnOwner.AGENT
    info: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status.terminal and self.owner is not TurnOwner.TERMINAL:
            raise ValueError("terminal frame must be owned by TERMINAL")
        if not self.status.terminal and self.owner is TurnOwner.TERMINAL:
            raise ValueError("non-terminal frame cannot be owned by TERMINAL")

    def observation(self) -> BalatroState:
        """Return an isolated copy of the canonical public observation."""

        return self.state.copy()


@dataclass(frozen=True)
class BackendStep:
    frame: EnvStateFrame
    reward: float = 0.0
    truncated: bool = False
