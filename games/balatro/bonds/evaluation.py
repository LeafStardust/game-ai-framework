from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from games.balatro.bonds.burnt import evaluate_hand_leveling_bond
from games.balatro.bonds.catalogue_batch_one import BATCH_ONE_EVALUATORS
from games.balatro.bonds.catalogue_batch_two import BATCH_TWO_EVALUATORS
from games.balatro.bonds.catalogue_batch_three import BATCH_THREE_EVALUATORS
from games.balatro.bonds.catalogue_batch_four import BATCH_FOUR_EVALUATORS
from games.balatro.bonds.catalogue_batch_five import BATCH_FIVE_EVALUATORS
from games.balatro.bonds.composer import Composition, compose_build
from games.balatro.bonds.held_cards import evaluate_held_cards_bond
from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.no_face_cards import evaluate_no_face_cards_bond
from games.balatro.bonds.realization import FROZEN_BOND_IDS, realize_bond
from games.balatro.bonds.strategy_development import reinforce_developments
from games.balatro.bonds.strategy_semantics import pinned_strategy
from games.balatro.bonds.vampire import evaluate_enhancement_consumption_bond

BondEvaluator = Callable[[Any], BondDevelopment]


def _canonical_id_adapter(evaluator: BondEvaluator, bond_id: str) -> BondEvaluator:
    """Temporary migration bridge for a legacy evaluator implementation."""
    def adapted(state: Any) -> BondDevelopment:
        development = evaluator(state)
        return development if development.bond_id == bond_id else replace(development, bond_id=bond_id)
    return adapted


EVALUATORS: dict[str, BondEvaluator] = {}
for family in (
    BATCH_ONE_EVALUATORS,
    BATCH_TWO_EVALUATORS,
    BATCH_THREE_EVALUATORS,
    BATCH_FOUR_EVALUATORS,
    BATCH_FIVE_EVALUATORS,
):
    overlap = set(EVALUATORS).intersection(family)
    if overlap:
        raise RuntimeError(f"Duplicate Bond evaluator registration: {sorted(overlap)}")
    EVALUATORS.update(family)

# `gold_economy` still lives in a legacy catalogue batch. Keep the compatibility
# bridge local and explicit so it can be deleted when that batch is migrated.
_legacy_gold = EVALUATORS.pop("gold_economy", None)
if _legacy_gold is not None:
    EVALUATORS["gold_cards"] = _canonical_id_adapter(_legacy_gold, "gold_cards")

for bond_id, evaluator in {
    "hand_leveling": evaluate_hand_leveling_bond,
    "held_cards": evaluate_held_cards_bond,
    "no_face_cards": evaluate_no_face_cards_bond,
    "enhancement_consumption": evaluate_enhancement_consumption_bond,
}.items():
    if bond_id in EVALUATORS:
        raise RuntimeError(f"Duplicate Bond evaluator registration: {bond_id}")
    EVALUATORS[bond_id] = evaluator


def missing_evaluators() -> tuple[str, ...]:
    return tuple(sorted(set(FROZEN_BOND_IDS) - set(EVALUATORS)))


def extra_evaluators() -> tuple[str, ...]:
    return tuple(sorted(set(EVALUATORS) - set(FROZEN_BOND_IDS)))


def evaluate_all_bonds(state: Any) -> tuple[BondDevelopment, ...]:
    """Evaluate and realize the frozen Bond catalogue from one live game state."""
    missing = missing_evaluators()
    extras = extra_evaluators()
    if missing or extras:
        raise RuntimeError(
            f"Bond evaluator registry mismatch: missing={missing!r} extras={extras!r}"
        )
    developments = []
    for bond_id in FROZEN_BOND_IDS:
        development = EVALUATORS[bond_id](state)
        if development.bond_id != bond_id:
            raise AssertionError(
                f"Bond evaluator {bond_id!r} returned {development.bond_id!r}"
            )
        developments.append(realize_bond(development, state))
    return tuple(developments)


def evaluate_bond_composition(state: Any) -> tuple[tuple[BondDevelopment, ...], Composition]:
    """Legacy composition entry point retained only while consumers migrate."""
    raw = evaluate_all_bonds(state)
    initial = compose_build(state, raw)
    pinned = pinned_strategy(initial.strategy_candidates)
    reinforced = reinforce_developments(raw, pinned)
    if reinforced == raw:
        return raw, initial

    realized = tuple(realize_bond(dev, state) for dev in reinforced)
    return realized, compose_build(state, realized)
