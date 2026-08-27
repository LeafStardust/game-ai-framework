from __future__ import annotations

"""Canonical D1 evidence for Burnt Joker first-discard development.

Burnt Joker's first discard permanently levels the discarded poker hand. This is
candidate-specific strategy evidence, not authority to choose the Play/Discard
class. The installer therefore augments strategy-fit evidence only; canonical D1
continues to own survival ordering and final arbitration.
"""

from games.balatro.actions import DISCARD_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


BURNT_TARGET_FIT = 2.0
BURNT_GENERIC_FIRST_DISCARD_FIT = 0.5


def _burnt_development(state):
    try:
        developments, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError):
        return None
    if "burnt" not in set(composition.bond_ids):
        return None
    return next(
        (
            development
            for development in developments
            if development.bond_id == "burnt"
            and development.unlocked
            and development.rank >= BondRank.R1
        ),
        None,
    )


def _first_discard_available(state) -> bool:
    used = getattr(state, "discards_used", None)
    if used is not None:
        try:
            return int(used or 0) == 0
        except (TypeError, ValueError):
            return False
    total = getattr(state, "discards_total", None)
    remaining = getattr(state, "discards_remaining", None)
    if total is None or remaining is None:
        return False
    try:
        return int(total or 0) == int(remaining or 0)
    except (TypeError, ValueError):
        return False


def _target_hand(development) -> str:
    return str(getattr(development, "target", None) or "HIGH_CARD").upper()


def _discard_hand_type(evaluator: HandEvaluator, state, action) -> str:
    try:
        cards = list(action.cards)
        if not cards:
            return ""
        return str(
            evaluator.evaluate(cards, rules=hand_rules_for_state(state)).value
        ).upper()
    except (AttributeError, TypeError, ValueError):
        return ""


def install_burnt_bond_execution_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_burnt_bond_execution_installed",
        False,
    ):
        return

    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit
    hand_evaluator = HandEvaluator()

    def strategy_fit(self, state, action):
        value, rationale = original_strategy_fit(self, state, action)
        if action.name != DISCARD_CARDS:
            return value, rationale
        development = _burnt_development(state)
        if development is None or not _first_discard_available(state):
            return value, rationale
        if int(getattr(state, "discards_remaining", 0) or 0) <= 1:
            return value, rationale
        if int(getattr(state, "hands_remaining", 0) or 0) <= 1:
            return value, rationale

        target = _target_hand(development)
        hand_type = _discard_hand_type(hand_evaluator, state, action)
        fit = BURNT_GENERIC_FIRST_DISCARD_FIT
        notes = [
            "Burnt first-discard evidence: this already-admitted DISCARD can create permanent hand-level growth",
        ]
        if hand_type == target:
            fit += BURNT_TARGET_FIT
            notes.append(f"Burnt target={target}; discarded poker hand matches target")
        else:
            notes.append(f"Burnt target={target}; discarded poker hand={hand_type or 'UNKNOWN'}")
        notes.append(
            "Burnt fit is subordinate to canonical D1 full-blind survival/resource ordering"
        )
        return value + fit, (*rationale, *notes)

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy._burnt_bond_execution_installed = True
