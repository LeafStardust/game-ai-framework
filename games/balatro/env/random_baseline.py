"""Reproducible random-legal strategic baseline for B0 evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_VERSION,
    action_from_index,
    legal_action_mask,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner


RANDOM_LEGAL_BASELINE_VERSION = "balatro-random-legal-baseline-v1"


class RandomLegalBaselineError(ValueError):
    """Raised when no exact random-baseline decision can be made."""


@dataclass(frozen=True)
class RandomLegalDecision:
    baseline_version: str
    observation_version: str
    action_version: str
    decision_number: int
    action_index: int
    action: EnvAction


class RandomLegalStrategicBaseline:
    """Uniformly select among exact legal action slots using an isolated stream.

    This is policy sampling authority, not Balatro mechanics RNG. A SHA-256
    counter stream makes the sequence portable and reproducible without reading
    or advancing ``HeadlessRunState`` RNG.
    """

    def __init__(self, seed: str | int):
        if isinstance(seed, bool) or not isinstance(seed, (str, int)):
            raise TypeError("baseline seed must be a string or exact integer")
        self._seed = str(seed)
        self._decision_number = 0

    @property
    def decision_number(self) -> int:
        return self._decision_number

    def _uniform_offset(self, size: int) -> int:
        if size <= 0:
            raise RandomLegalBaselineError("random selection requires a nonempty legal mask")
        counter = 0
        limit = (1 << 256) - ((1 << 256) % size)
        while True:
            payload = (
                f"{RANDOM_LEGAL_BASELINE_VERSION}\0{self._seed}\0"
                f"{self._decision_number}\0{counter}"
            ).encode("utf-8")
            value = int.from_bytes(sha256(payload).digest(), "big")
            if value < limit:
                return value % size
            counter += 1

    def select(
        self,
        frame: EnvStateFrame,
        legal_actions: Iterable[EnvAction],
    ) -> RandomLegalDecision | None:
        if not isinstance(frame, EnvStateFrame):
            raise TypeError("frame must be EnvStateFrame")

        actions = tuple(legal_actions)
        if frame.status.terminal:
            if actions:
                raise RandomLegalBaselineError("terminal frame cannot expose legal actions")
            return None
        if frame.status is not RunStatus.RUNNING or frame.owner is not TurnOwner.AGENT:
            raise RandomLegalBaselineError("random strategic selection requires an agent-owned running frame")

        # Validate the policy-facing state and canonical action vocabulary at the
        # decision boundary. Neither result contains private game RNG authority.
        observation = frame.encoded_observation()
        if observation.schema_version != PUBLIC_OBSERVATION_VERSION:
            raise RandomLegalBaselineError("observation schema version mismatch")
        mask = legal_action_mask(actions)
        if mask.schema_version != PUBLIC_ACTION_VERSION:
            raise RandomLegalBaselineError("action schema version mismatch")
        legal_indices = tuple(index for index, allowed in enumerate(mask.values) if allowed)
        if not legal_indices:
            raise RandomLegalBaselineError("nonterminal agent frame has an empty legal action mask")

        decision_number = self._decision_number
        selected_index = legal_indices[self._uniform_offset(len(legal_indices))]
        self._decision_number += 1
        return RandomLegalDecision(
            RANDOM_LEGAL_BASELINE_VERSION,
            observation.schema_version,
            mask.schema_version,
            decision_number,
            selected_index,
            action_from_index(selected_index),
        )
