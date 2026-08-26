from __future__ import annotations

"""Stable Castle discard execution semantics.

Castle may improve an already-required discard by preferring cards of its current
public suit, but it never creates a discard or materially weakens survival.  This
is a Joker-mechanics execution rule, not strategy authority.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS
from games.balatro.live.hand_action_policy import LiveHandActionPolicy


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _castle_suit(state) -> str | None:
    for joker in getattr(state, "jokers", ()) or ():
        if _joker_token(joker) not in {"castle", "castlejoker"}:
            continue
        public = getattr(joker, "public_state", None)
        if isinstance(public, dict):
            suit = public.get("suit")
        else:
            suit = getattr(public, "suit", None) if public is not None else None
        suit = suit or getattr(joker, "suit", None) or getattr(joker, "current_suit", None)
        if suit:
            return str(suit)
    return None


def _castle_match_count(plan, suit: str) -> int:
    return sum(
        1
        for card in (getattr(plan.action, "cards", ()) or ())
        if str(getattr(card, "suit", "")) == suit
    )


def _safe_castle_discard_alternative(result, suit: str):
    selected = result.selected_plan
    if selected.action.name != DISCARD_CARDS:
        return None
    if _castle_match_count(selected, suit) > 0:
        return None

    selected_probability = float(selected.value.clear_probability)
    selected_score = float(selected.value.expected_score)
    tolerance = float(
        getattr(getattr(result, "thresholds", None), "safe_clear_probability_tolerance", 0.0)
        or 0.0
    )
    candidates = []
    for plan in result.plans:
        if plan.action.name != DISCARD_CARDS:
            continue
        matches = _castle_match_count(plan, suit)
        if matches <= 0:
            continue
        probability = float(plan.value.clear_probability)
        expected_score = float(plan.value.expected_score)
        if probability + tolerance + 1e-9 < selected_probability:
            continue
        if selected_score > 0.0 and expected_score + 1e-9 < 0.90 * selected_score:
            continue
        if bool(getattr(selected, "exact", False)) and not bool(getattr(plan, "exact", False)):
            continue
        candidates.append((matches, probability, expected_score, plan))

    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1], item[2]))[3]


def install_castle_discard_policy() -> None:
    if getattr(LiveHandActionPolicy, "_castle_discard_policy_installed", False):
        return

    original_decide = LiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        result = original_decide(self, state, plans, **kwargs)
        if result.action.name != DISCARD_CARDS:
            return result

        suit = _castle_suit(state)
        if not suit:
            return result
        alternative = _safe_castle_discard_alternative(result, suit)
        if alternative is None:
            return result

        tolerance = float(
            getattr(getattr(result, "thresholds", None), "safe_clear_probability_tolerance", 0.0)
            or 0.0
        )
        return replace(
            result,
            action=alternative.action,
            selected_plan=alternative,
            selected_fallback_value=float(self.evaluator.evaluate(state, alternative.action)),
            rationale=(
                f"Castle execution: an already-required discard can include current Castle suit {suit} without material survival loss",
                f"Castle alternative must remain within canonical D1 clear-probability tolerance={tolerance:.3f}",
                "Castle never creates a discard and rejects materially weaker alternatives",
                *result.rationale,
            ),
        )

    LiveHandActionPolicy.decide = decide
    LiveHandActionPolicy._castle_discard_policy_installed = True
