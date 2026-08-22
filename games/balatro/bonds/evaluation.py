from __future__ import annotations

from typing import Any, Callable

from games.balatro.bonds.burnt import evaluate_burnt_bond
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
from games.balatro.bonds.vampire import evaluate_vampire_bond

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

for bond_id, evaluator in {
    "burnt": evaluate_burnt_bond,
    "held_cards": evaluate_held_cards_bond,
    "no_face_cards": evaluate_no_face_cards_bond,
    "vampire": evaluate_vampire_bond,
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
    developments = evaluate_all_bonds(state)
    return developments, compose_build(state, developments)
