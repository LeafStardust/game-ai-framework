"""R0 facade for a deterministic headless Balatro backend.

The facade owns API/episode invariants only. Exact game transitions, RNG and
serialization remain backend responsibilities implemented in later Phase-R work;
R0 deliberately does not approximate missing Balatro mechanics.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from games.balatro.env.actions import EnvAction, validate_training_action
from games.balatro.env.state import BackendStep, EnvStateFrame, TurnOwner


@runtime_checkable
class HeadlessBackend(Protocol):
    """Exact deterministic backend boundary to be filled by R1/R2."""

    def reset(self, seed: str | int) -> EnvStateFrame: ...

    def step(self, action: EnvAction) -> BackendStep: ...

    def legal_actions(self) -> tuple[EnvAction, ...]: ...

    def serialize(self) -> dict[str, Any]: ...

    def restore(self, payload: dict[str, Any]) -> EnvStateFrame: ...


class BalatroHeadlessEnvironment:
    """Gym-like single-agent API over an exact deterministic backend."""

    def __init__(self, backend: HeadlessBackend):
        if not isinstance(backend, HeadlessBackend):
            raise TypeError("backend does not satisfy HeadlessBackend")
        self._backend = backend
        self._frame: EnvStateFrame | None = None

    @property
    def frame(self) -> EnvStateFrame:
        if self._frame is None:
            raise RuntimeError("environment has not been reset")
        return self._frame

    def reset(self, *, seed: str | int) -> tuple[object, dict[str, Any]]:
        frame = self._backend.reset(seed)
        self._validate_frame(frame)
        self._frame = frame
        return frame.observation(), dict(frame.info)

    def legal_actions(self) -> tuple[EnvAction, ...]:
        frame = self.frame
        if frame.status.terminal or frame.owner is not TurnOwner.AGENT:
            return ()
        actions = tuple(self._backend.legal_actions())
        for action in actions:
            validate_training_action(action)
        if len(actions) != len(set(actions)):
            raise ValueError("backend exposed duplicate legal actions")
        return actions

    def step(self, action: EnvAction) -> tuple[object, float, bool, bool, dict[str, Any]]:
        frame = self.frame
        if frame.status.terminal:
            raise RuntimeError("cannot step a terminal environment")
        if frame.owner is not TurnOwner.AGENT:
            raise RuntimeError(f"agent cannot act while turn owner is {frame.owner.value}")
        validate_training_action(action)
        if action not in self.legal_actions():
            raise ValueError(f"illegal action: {action.alias}")

        result = self._backend.step(action)
        self._validate_frame(result.frame)
        self._frame = result.frame
        return (
            result.frame.observation(),
            float(result.reward),
            result.frame.status.terminal,
            bool(result.truncated),
            dict(result.frame.info),
        )

    def serialize(self) -> dict[str, Any]:
        self.frame
        return self._backend.serialize()

    def restore(self, payload: dict[str, Any]) -> tuple[object, dict[str, Any]]:
        frame = self._backend.restore(payload)
        self._validate_frame(frame)
        self._frame = frame
        return frame.observation(), dict(frame.info)

    @staticmethod
    def _validate_frame(frame: EnvStateFrame) -> None:
        if not isinstance(frame, EnvStateFrame):
            raise TypeError("backend must return EnvStateFrame")
