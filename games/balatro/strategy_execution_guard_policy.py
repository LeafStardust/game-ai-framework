from __future__ import annotations

"""Pure D1 evidence helpers for realized repetition and Green preservation.

Canonical D1 owns the Play/Discard hierarchy. Repetition fit and the narrow Green
Joker preservation rule are consumed natively by ``StrategyAwareLiveHandActionPolicy``;
this module no longer mutates that policy at import time.

Pure compatibility helpers remain for deterministic regression tests.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.hand_rules import hand_rules_for_state


HAND_REPETITION_FIT = 2.0


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "label", None)
        or getattr(joker, "name", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    token = _normalize(value)
    return token if token.endswith("joker") else token + "joker"


def _realized_bond(state, bond_id: str) -> bool:
    try:
        diagnostics = bond_strategy_diagnostics(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return False
    for payload in diagnostics.get("relevant_bonds", ()) or ():
        if str(payload.get("bond_id")) != bond_id:
            continue
        return str(payload.get("realization", "")).upper() in {"ACTIVE", "MATURE"}
    return False


def realized_banner_delayed_no_discard(state) -> bool:
    """Compatibility predicate retained for deterministic regressions."""
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return {"bannerjoker", "delayedgratificationjoker"}.issubset(owned)


def _realized_no_discard_engine(state) -> bool:
    """Compatibility evidence predicate for legacy deterministic regressions."""
    if not _realized_bond(state, "no_discard"):
        return False
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return bool(owned & {"greenjoker", "delayedgratificationjoker", "bannerjoker"})


def _green_joker_active(state) -> bool:
    return any(
        _joker_token(joker) == "greenjoker"
        for joker in getattr(state, "jokers", ()) or ()
    )


def _plan_clear_probability(plan) -> float:
    try:
        return float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _green_preserving_play(policy, state, plans, decision):
    """Return the best survival-equivalent PLAY when Green would otherwise discard."""
    if getattr(getattr(decision, "action", None), "name", None) != DISCARD_CARDS:
        return None
    if not _green_joker_active(state):
        return None

    selected_probability = _plan_clear_probability(getattr(decision, "selected_plan", None))
    try:
        tolerance = float(
            getattr(
                getattr(decision, "thresholds", None),
                "safe_clear_probability_tolerance",
                0.0,
            )
            or 0.0
        )
    except (TypeError, ValueError):
        tolerance = 0.0

    candidates = [
        plan
        for plan in plans
        if getattr(getattr(plan, "action", None), "name", None) == PLAY_CARDS
        and _plan_clear_probability(plan) + tolerance + policy.EPSILON
        >= selected_probability
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda plan: (
            _plan_clear_probability(plan),
            1 if bool(getattr(plan, "exact", False)) else 0,
            float(getattr(plan.value, "expected_progress", 0.0) or 0.0),
            float(getattr(plan.value, "expected_hands_remaining", 0.0) or 0.0),
            float(getattr(plan.value, "expected_discards_remaining", 0.0) or 0.0),
            float(getattr(plan.value, "expected_score", 0.0) or 0.0),
        ),
    )


def _played_this_round(state) -> set[str]:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        counts = getattr(state, "hand_play_counts_this_round", None)
    if not isinstance(counts, dict):
        return set()
    return {_normalize(name) for name, count in counts.items() if int(count or 0) > 0}


def _hand_key(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return _normalize(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    )


def _selected_clear_probability(decision) -> float:
    selected = getattr(decision, "selected_plan", None)
    try:
        return float(getattr(selected.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _clear_probability_tolerance(decision) -> float:
    try:
        return float(
            getattr(
                getattr(decision, "thresholds", None),
                "safe_clear_probability_tolerance",
                0.0,
            )
            or 0.0
        )
    except (TypeError, ValueError):
        return 0.0


def _safe_pace_play(policy, state, plans, decision):
    """Legacy pure selector retained only for regression compatibility."""
    selected_probability = _selected_clear_probability(decision)
    tolerance = _clear_probability_tolerance(decision)
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS:
            continue
        probability = float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
        if probability + tolerance + policy.EPSILON < selected_probability:
            continue
        score = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        if pace_target > 0.0 and score + policy.EPSILON < pace_target:
            continue
        candidates.append((probability, score, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[0],
            policy._strategy_fit(state, item[2].action)[0],
            item[1],
            policy._within_type_key(item[2]),
        ),
    )


def _safe_repeat_play(policy, state, plans, decision):
    """Legacy pure selector retained only for regression compatibility."""
    if not _realized_bond(state, "hand_repetition"):
        return None
    repeated = _played_this_round(state)
    if not repeated:
        return None

    selected_probability = _selected_clear_probability(decision)
    tolerance = _clear_probability_tolerance(decision)
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS or _hand_key(policy, state, plan) not in repeated:
            continue
        probability = float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
        if probability + tolerance + policy.EPSILON < selected_probability:
            continue
        score = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        if pace_target > 0.0 and score + policy.EPSILON < pace_target:
            continue
        candidates.append((probability, score, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[0],
            policy._strategy_fit(state, item[2].action)[0],
            item[1],
            policy._within_type_key(item[2]),
        ),
    )


def _play_repeats_hand(policy, state, action) -> bool:
    if action.name != PLAY_CARDS or not _realized_bond(state, "hand_repetition"):
        return False
    repeated = _played_this_round(state)
    if not repeated:
        return False
    rules = hand_rules_for_state(state)
    hand = policy._hand_evaluator.evaluate(list(action.cards), rules=rules)
    return _normalize(hand.value) in repeated
