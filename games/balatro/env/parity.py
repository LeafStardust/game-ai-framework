"""Canonical public evidence comparison for live/headless Balatro parity.

R5 compares policy-visible state/action/transition evidence. It deliberately does
not compare simulator-private run authority, RNG objects, physical draw order, or
engine-local object identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.state import BalatroState


# Engine/local object identity is not gameplay evidence and is not stable across
# a live process and the headless simulator. Selected tactical cards are compared
# by their visible hand positions instead.
_IDENTITY_FIELDS = frozenset({"live_id", "area_index"})


def _canonical_public_value(value: Any):
    """Convert policy-visible model state into a deterministic comparison value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return (type(value).__name__, value.value)
    if isinstance(value, dict):
        return tuple(
            sorted(
                (str(key), _canonical_public_value(item))
                for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_public_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_canonical_public_value(item) for item in value), key=repr))
    if hasattr(value, "__dict__"):
        return (
            type(value).__name__,
            tuple(
                (name, _canonical_public_value(item))
                for name, item in sorted(vars(value).items())
                if name not in _IDENTITY_FIELDS
            ),
        )
    raise TypeError(
        f"R5 public parity does not know how to canonicalize {type(value).__name__}"
    )


def canonical_public_state_signature(state: BalatroState) -> tuple:
    """Return deterministic, identity-free policy-visible state evidence."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    return _canonical_public_value(public_observation_state(state))


@dataclass(frozen=True)
class PublicTacticalParitySignature:
    """Canonical R5 signature for one tactical transition."""

    before: tuple
    action_name: str
    selected_hand_indices: tuple[int, ...]
    after: tuple


@dataclass(frozen=True)
class PublicTacticalParityComparison:
    """Result of comparing one live and one simulator tactical transition."""

    matches: bool
    differences: tuple[str, ...]
    live: PublicTacticalParitySignature
    simulator: PublicTacticalParitySignature


@dataclass(frozen=True)
class PublicTacticalTrajectoryParityComparison:
    """Ordered R5 parity result for a tactical trajectory."""

    matches: bool
    differences: tuple[str, ...]
    live_length: int
    simulator_length: int
    steps: tuple[PublicTacticalParityComparison, ...]


def canonical_tactical_evidence_signature(
    evidence: PublicTacticalTransitionEvidence,
) -> PublicTacticalParitySignature:
    """Canonicalize existing R4 evidence without introducing a second action schema."""
    if not isinstance(evidence, PublicTacticalTransitionEvidence):
        raise TypeError("evidence must be PublicTacticalTransitionEvidence")
    return PublicTacticalParitySignature(
        before=canonical_public_state_signature(evidence.before),
        action_name=evidence.action.name,
        selected_hand_indices=tuple(evidence.selected_hand_indices),
        after=canonical_public_state_signature(evidence.after),
    )


def compare_public_tactical_evidence(
    live_evidence: PublicTacticalTransitionEvidence,
    simulator_evidence: PublicTacticalTransitionEvidence,
) -> PublicTacticalParityComparison:
    """Compare canonical public tactical evidence from live and headless execution."""
    live = canonical_tactical_evidence_signature(live_evidence)
    simulator = canonical_tactical_evidence_signature(simulator_evidence)
    differences: list[str] = []
    if live.before != simulator.before:
        differences.append("before")
    if live.action_name != simulator.action_name:
        differences.append("action.name")
    if live.selected_hand_indices != simulator.selected_hand_indices:
        differences.append("action.selected_hand_indices")
    if live.after != simulator.after:
        differences.append("after")
    return PublicTacticalParityComparison(
        matches=not differences,
        differences=tuple(differences),
        live=live,
        simulator=simulator,
    )


def compare_public_tactical_trajectory(
    live_evidence: Iterable[PublicTacticalTransitionEvidence],
    simulator_evidence: Iterable[PublicTacticalTransitionEvidence],
) -> PublicTacticalTrajectoryParityComparison:
    """Compare ordered live/headless tactical trajectories without repairing gaps.

    Length and step order are parity evidence. The comparator therefore never
    truncates one trajectory to make it match the other: overlapping steps are
    compared canonically and any length mismatch is reported explicitly.
    """
    live = tuple(live_evidence)
    simulator = tuple(simulator_evidence)
    steps = tuple(
        compare_public_tactical_evidence(live_step, simulator_step)
        for live_step, simulator_step in zip(live, simulator)
    )

    differences: list[str] = []
    if len(live) != len(simulator):
        differences.append("length")
    for index, comparison in enumerate(steps):
        differences.extend(
            f"step[{index}].{difference}"
            for difference in comparison.differences
        )

    return PublicTacticalTrajectoryParityComparison(
        matches=not differences,
        differences=tuple(differences),
        live_length=len(live),
        simulator_length=len(simulator),
        steps=steps,
    )
