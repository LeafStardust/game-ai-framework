from __future__ import annotations

"""Pure Castle discard evidence for canonical D1 strategy evaluation.

Castle rewards discarding cards of its current public suit. The mechanic is useful
only as a preference among discard candidates already admitted by canonical D1.
Production applies this evidence directly from ``StrategyAwareLiveHandActionPolicy``;
this module contains only public-state helpers plus the legacy deterministic selector
used by compatibility regressions.
"""

from games.balatro.actions import DISCARD_CARDS


CASTLE_MATCH_FIT = 0.75


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


def _castle_match_count(action, suit: str) -> int:
    if action.name != DISCARD_CARDS:
        return 0
    return sum(
        1
        for card in (getattr(action, "cards", ()) or ())
        if str(getattr(card, "suit", "")) == suit
    )


def _castle_strategy_fit(state, action) -> tuple[float, tuple[str, ...]]:
    """Return subordinate Castle evidence for one already-legal D1 action."""
    suit = _castle_suit(state)
    if not suit:
        return 0.0, ()
    matches = _castle_match_count(action, suit)
    if matches <= 0:
        return 0.0, ()
    return (
        CASTLE_MATCH_FIT * matches,
        (
            f"Castle discard evidence: {matches} discarded card(s) match current suit {suit}",
            "Castle fit is subordinate to canonical D1 full-blind survival/resource ordering",
        ),
    )


def _safe_castle_discard_alternative(result, suit: str):
    """Legacy pure selector retained only for deterministic compatibility tests."""
    selected = result.selected_plan
    if selected.action.name != DISCARD_CARDS:
        return None
    if _castle_match_count(selected.action, suit) > 0:
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
        matches = _castle_match_count(plan.action, suit)
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
