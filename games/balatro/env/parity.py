"""Canonical public evidence comparison for live/headless Balatro parity.

R5 compares policy-visible state/action/transition evidence. It deliberately does
not compare simulator-private run authority, RNG objects, physical draw order, or
engine-local object identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from copy import copy
from typing import Any, Iterable

from games.balatro.env.joker_centers import joker_rarity_id
from games.balatro.env.shop_consumable_generation_state import (
    _visible_consumable_record,
)
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.strategic_evidence import PublicStrategicTransitionEvidence
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.state import BalatroState


_IDENTITY_FIELDS = frozenset({"live_id", "area_index"})


def _canonical_public_value(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return (type(value).__name__, value.value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _canonical_public_value(item)) for key, item in value.items()))
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
    raise TypeError(f"R5 public parity does not know how to canonicalize {type(value).__name__}")


def canonical_public_state_signature(state: BalatroState) -> tuple:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    observation = public_observation_state(state)
    normalized = copy(observation)
    normalized.shop_jokers = [
        _canonical_shop_joker(item)
        for item in observation.shop_jokers
    ]
    normalized.shop_consumables = [
        _canonical_shop_consumable(item)
        for item in observation.shop_consumables
    ]
    return _canonical_public_value(normalized)


def _exact_public_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if value is None:
        value = getattr(item, "cost", None)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if type(value) is not int or value < 0:
        raise TypeError("R5 public shop item price must be an exact nonnegative integer")
    return value


def _canonical_shop_joker(item: Any) -> tuple:
    center = getattr(item, "center_key", None) or getattr(item, "center", None)
    if not isinstance(center, str) or not center:
        raise TypeError("R5 public shop Joker center must be exact")
    rarity = getattr(item, "rarity", None)
    if isinstance(rarity, str):
        rarity = rarity.title()
    try:
        rarity_id = joker_rarity_id(rarity)
    except (TypeError, ValueError) as exc:
        raise TypeError("R5 public shop Joker rarity must be exact") from exc
    edition = getattr(item, "edition", None)
    normalized_edition = str(edition).upper() if edition else None
    return ("JOKER", center, rarity_id, normalized_edition, _exact_public_price(item))


def _canonical_shop_consumable(item: Any) -> tuple:
    record = _visible_consumable_record(item)
    if record is None:
        raise TypeError("R5 public shop consumable identity must be exact")
    return (
        "CONSUMABLE",
        record["type"],
        record["key"],
        _exact_public_price(item),
    )


@dataclass(frozen=True)
class PublicTacticalParitySignature:
    before: tuple
    action_name: str
    selected_hand_indices: tuple[int, ...]
    after: tuple


@dataclass(frozen=True)
class PublicTacticalParityComparison:
    matches: bool
    differences: tuple[str, ...]
    live: PublicTacticalParitySignature
    simulator: PublicTacticalParitySignature


@dataclass(frozen=True)
class PublicTacticalTrajectoryParityComparison:
    matches: bool
    differences: tuple[str, ...]
    live_length: int
    simulator_length: int
    steps: tuple[PublicTacticalParityComparison, ...]


@dataclass(frozen=True)
class PublicStrategicParitySignature:
    before: tuple
    action_id: str
    action_params: tuple
    after: tuple


@dataclass(frozen=True)
class PublicStrategicParityComparison:
    matches: bool
    differences: tuple[str, ...]
    live: PublicStrategicParitySignature
    simulator: PublicStrategicParitySignature


@dataclass(frozen=True)
class PublicStrategicTrajectoryParityComparison:
    matches: bool
    differences: tuple[str, ...]
    live_length: int
    simulator_length: int
    steps: tuple[PublicStrategicParityComparison, ...]


def canonical_tactical_evidence_signature(evidence: PublicTacticalTransitionEvidence) -> PublicTacticalParitySignature:
    if not isinstance(evidence, PublicTacticalTransitionEvidence):
        raise TypeError("evidence must be PublicTacticalTransitionEvidence")
    return PublicTacticalParitySignature(
        before=canonical_public_state_signature(evidence.before),
        action_name=evidence.action.name,
        selected_hand_indices=tuple(evidence.selected_hand_indices),
        after=canonical_public_state_signature(evidence.after),
    )


def compare_public_tactical_evidence(live_evidence: PublicTacticalTransitionEvidence, simulator_evidence: PublicTacticalTransitionEvidence) -> PublicTacticalParityComparison:
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
    return PublicTacticalParityComparison(not differences, tuple(differences), live, simulator)


def compare_public_tactical_trajectory(live_evidence: Iterable[PublicTacticalTransitionEvidence], simulator_evidence: Iterable[PublicTacticalTransitionEvidence]) -> PublicTacticalTrajectoryParityComparison:
    live = tuple(live_evidence)
    simulator = tuple(simulator_evidence)
    steps = tuple(compare_public_tactical_evidence(a, b) for a, b in zip(live, simulator))
    differences: list[str] = []
    if len(live) != len(simulator):
        differences.append("length")
    for index, comparison in enumerate(steps):
        differences.extend(f"step[{index}].{difference}" for difference in comparison.differences)
    return PublicTacticalTrajectoryParityComparison(not differences, tuple(differences), len(live), len(simulator), steps)


def canonical_strategic_evidence_signature(evidence: PublicStrategicTransitionEvidence) -> PublicStrategicParitySignature:
    """Canonicalize an R3 strategic evidence record without inventing action IDs."""
    if not isinstance(evidence, PublicStrategicTransitionEvidence):
        raise TypeError("evidence must be PublicStrategicTransitionEvidence")
    payload = evidence.action.payload()
    params = tuple((key, _canonical_public_value(value)) for key, value in sorted(payload.items()) if key != "action_id")
    return PublicStrategicParitySignature(
        before=canonical_public_state_signature(evidence.before),
        action_id=evidence.action.action_id,
        action_params=params,
        after=canonical_public_state_signature(evidence.after),
    )


def compare_public_strategic_evidence(live_evidence: PublicStrategicTransitionEvidence, simulator_evidence: PublicStrategicTransitionEvidence) -> PublicStrategicParityComparison:
    live = canonical_strategic_evidence_signature(live_evidence)
    simulator = canonical_strategic_evidence_signature(simulator_evidence)
    differences: list[str] = []
    if live.before != simulator.before:
        differences.append("before")
    if live.action_id != simulator.action_id:
        differences.append("action.id")
    if live.action_params != simulator.action_params:
        differences.append("action.params")
    if live.after != simulator.after:
        differences.append("after")
    return PublicStrategicParityComparison(not differences, tuple(differences), live, simulator)


def compare_public_strategic_trajectory(live_evidence: Iterable[PublicStrategicTransitionEvidence], simulator_evidence: Iterable[PublicStrategicTransitionEvidence]) -> PublicStrategicTrajectoryParityComparison:
    """Compare ordered strategic transitions; never truncate/repair mismatched paths."""
    live = tuple(live_evidence)
    simulator = tuple(simulator_evidence)
    steps = tuple(compare_public_strategic_evidence(a, b) for a, b in zip(live, simulator))
    differences: list[str] = []
    if len(live) != len(simulator):
        differences.append("length")
    for index, comparison in enumerate(steps):
        differences.extend(f"step[{index}].{difference}" for difference in comparison.differences)
    return PublicStrategicTrajectoryParityComparison(not differences, tuple(differences), len(live), len(simulator), steps)
