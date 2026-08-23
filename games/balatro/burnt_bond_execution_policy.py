from __future__ import annotations

"""Canonical Burnt-Bond D1 execution authority.

Burnt Joker's value is permanent first-discard hand leveling.  Generic D1 survival
must remain authoritative, but a selected Burnt Bond must not be silently suppressed
by Banner's immediate remaining-discard chips or by the generic rule that a
pace-qualified play outranks strategic shaping.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


MIN_SAFE_BURNT_CLEAR_PROBABILITY = 0.70
MAX_CLEAR_PROBABILITY_SACRIFICE = 0.08


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


def _clear_probability(plan) -> float:
    try:
        return float(plan.value.clear_probability)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _expected_score(plan) -> float:
    try:
        return float(plan.value.expected_score)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _target_hand(development) -> str:
    return str(getattr(development, "target", None) or "HIGH_CARD").upper()


def _discard_hand_type(evaluator: HandEvaluator, plan) -> str:
    try:
        cards = list(plan.action.cards)
        if not cards:
            return ""
        return str(evaluator.evaluate(cards).value).upper()
    except (AttributeError, TypeError, ValueError):
        return ""


def _safe_burnt_discard(decision, discards):
    if not discards:
        return None
    selected_probability = _clear_probability(decision.selected_plan)
    floor = max(
        MIN_SAFE_BURNT_CLEAR_PROBABILITY,
        selected_probability - MAX_CLEAR_PROBABILITY_SACRIFICE,
    )
    safe = [plan for plan in discards if _clear_probability(plan) >= floor]
    if safe:
        return safe

    # If the baseline itself has low modeled clear probability, do not pretend the
    # Burnt setup is safe. Survival remains above permanent scaling.
    return None


def install_burnt_bond_execution_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_burnt_bond_execution_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide
    hand_evaluator = HandEvaluator()

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)
        development = _burnt_development(state)
        if development is None:
            return decision
        if not _first_discard_available(state):
            return decision
        if int(getattr(state, "discards_remaining", 0) or 0) <= 1:
            return decision
        if int(getattr(state, "hands_remaining", 0) or 0) <= 1:
            return decision

        discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
        safe = _safe_burnt_discard(decision, discards)
        if not safe:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "Burnt Bond first-discard setup withheld because no discard line preserved the required modeled clear probability",
                    "survival remains authoritative over permanent Burnt scaling",
                ),
            )

        target = _target_hand(development)
        target_safe = [
            plan for plan in safe
            if _discard_hand_type(hand_evaluator, plan) == target
        ]
        candidates = target_safe or safe
        selected = max(
            candidates,
            key=lambda plan: (
                _clear_probability(plan),
                _expected_score(plan),
                -len(tuple(getattr(plan.action, "cards", ()) or ())),
                self._within_type_key(plan),
            ),
        )
        selected_probability = _clear_probability(selected)
        selected_type = _discard_hand_type(hand_evaluator, selected)
        value = float(self.evaluator.evaluate(state, selected.action))

        banner_owned = any(
            str(getattr(joker, "name", getattr(joker, "label", type(joker).__name__))).lower().replace(" ", "")
            in {"banner", "bannerjoker"}
            for joker in getattr(state, "jokers", ()) or ()
        )
        banner_note = (
            "Banner is owned: one remaining-discard chip payment is accepted because this safe first discard creates permanent Burnt hand-level growth"
            if banner_owned
            else "Burnt first-discard setup creates permanent hand-level growth"
        )

        return replace(
            decision,
            mode=PACE_RECOVERY,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=None,
            selected_pace_ratio=None,
            selected_fallback_value=value,
            confidence=max(float(decision.confidence), selected_probability),
            rationale=(
                f"Burnt Bond execution: activate the first-discard level before playing when survival remains safe",
                f"Burnt target={target}; selected discard hand={selected_type}; modeled clear probability={selected_probability:.3f}",
                banner_note,
                "canonical Burnt authority overrides the generic pace-qualified PLAY preference only for this first safe discard",
                *decision.rationale,
            ),
        )

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._burnt_bond_execution_installed = True
