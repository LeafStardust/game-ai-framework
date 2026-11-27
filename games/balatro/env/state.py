"""Canonical public-state frame and episode ownership semantics for Phase R."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from games.balatro.env.public_observation import public_observation_state
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
    """R0 wrapper around the existing canonical Balatro state."""

    state: BalatroState
    status: RunStatus = RunStatus.RUNNING
    owner: TurnOwner = TurnOwner.AGENT
    info: dict[str, Any] = field(default_factory=dict)
    pending_double_tags: int = 0
    pack_choices: tuple[Any, ...] = ()
    pack_choices_remaining: int = 0

    def __post_init__(self) -> None:
        if type(self.pack_choices_remaining) is not int or not (
            0 <= self.pack_choices_remaining <= len(self.pack_choices)
        ):
            raise ValueError("remaining pack picks require exact visible choices")
        if self.pack_choices and self.state.phase != "BUFFOON_PACK":
            raise ValueError("visible Joker pack choices require a Buffoon phase")
        if type(self.pending_double_tags) is not int or self.pending_double_tags < 0:
            raise ValueError("pending Double Tags require a nonnegative integer count")
        if self.status.terminal and self.owner is not TurnOwner.TERMINAL:
            raise ValueError("terminal frame must be owned by TERMINAL")
        if not self.status.terminal and self.owner is TurnOwner.TERMINAL:
            raise ValueError("non-terminal frame cannot be owned by TERMINAL")

    def observation(self) -> BalatroState:
        """Return an isolated policy-safe observation.

        Internal exact mechanics may retain hidden physical card identity. The
        policy boundary masks any face-down hand identity before exposure.
        """

        return public_observation_state(self.state)

    def encoded_observation(self):
        """Return the versioned fixed-shape policy representation."""
        from games.balatro.env.observation_encoding import encode_public_observation

        return encode_public_observation(self)


@dataclass(frozen=True)
class BackendStep:
    frame: EnvStateFrame
    reward: float = 0.0
    truncated: bool = False
