from __future__ import annotations

from typing import Any, Callable

from games.balatro.bonds.burnt import evaluate_hand_leveling_bond
from games.balatro.bonds.catalogue_batch_one import BATCH_ONE_EVALUATORS
from games.balatro.bonds.catalogue_batch_two import BATCH_TWO_EVALUATORS
from games.balatro.bonds.catalogue_batch_three import BATCH_THREE_EVALUATORS
from games.balatro.bonds.catalogue_batch_four import BATCH_FOUR_EVALUATORS
from games.balatro.bonds.catalogue_batch_five import BATCH_FIVE_EVALUATORS
from games.balatro.bonds.composer import Composition, compose_build
from games.balatro.bonds.gold_cards import evaluate_gold_cards_bond
from games.balatro.bonds.held_cards import evaluate_held_cards_bond
from games.balatro.bonds.mechanical_core import (
    evaluate_deck_thinning_bond,
    evaluate_held_retrigger_bond,
    evaluate_steel_bond,
)
from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.no_face_cards import evaluate_no_face_cards_bond
from games.balatro.bonds.realization import FROZEN_BOND_IDS, realize_bond
from games.balatro.bonds.strategy_development import reinforce_developments
from games.balatro.bonds.strategy_semantics import pinned_strategy
from games.balatro.bonds.vampire import evaluate_enhancement_consumption_bond

BondEvaluator = Callable[[Any], BondDevelopment]

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

# Legacy catalogue implementations remain temporarily for migration compatibility,
# but production evaluation must use the canonical mechanical evaluators below.
for legacy_id in (
    "gold_economy",
    "held_retrigger",
    "steel",
    "deck_thinning",
):
    EVALUATORS.pop(legacy_id, None)

for bond_id, evaluator in {
    "hand_leveling": evaluate_hand_leveling_bond,
    "gold_cards": evaluate_gold_cards_bond,
    "held_cards": evaluate_held_cards_bond,
    "held_retrigger": evaluate_held_retrigger_bond,
    "steel": evaluate_steel_bond,
    "deck_thinning": evaluate_deck_thinning_bond,
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
