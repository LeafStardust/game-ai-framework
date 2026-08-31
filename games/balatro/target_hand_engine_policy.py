from __future__ import annotations

"""Canonical D1 evidence for Runner and To Do List target-hand mechanics.

Canonical D1 owns the Play/Discard action class and all final candidate arbitration.
This module exposes pure target-hand evidence consumed by that policy; it does not
install or mutate production decision classes.

Pure legacy selection helpers remain callable for deterministic regression tests,
but are not installed into production arbitration.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.hand_rules import hand_rules_for_state


TARGET_HAND_FIT = 2.5


def _normalize(value: object) -> str:
    return "_".join(str(value or "").upper().replace("-", " ").replace("_", " ").split())


def _joker_name(joker: object) -> str:
    value = (
        getattr(joker, "label", None)
        or getattr(joker, "name", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _target_hands(state) -> tuple[str, ...]:
    targets: list[str] = []
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        name = _joker_name(joker)
        if name in {"runner", "runnerjoker"}:
            targets.extend(("STRAIGHT", "STRAIGHT_FLUSH"))
            continue
        if name in {"todolist", "todolistjoker"}:
            value = getattr(joker, "target_hand", None)
            if value is None:
                public = getattr(joker, "public_state", None)
                if isinstance(public, dict):
                    value = public.get("target_hand")
            normalized = _normalize(getattr(value, "value", value))
            if normalized:
                targets.append(normalized)
    return tuple(dict.fromkeys(targets))


def _plan_hand(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return _normalize(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    )


def _safe_target_play(policy, state, plans, decision):
    """Legacy pure selector retained only for deterministic compatibility tests."""
    targets = set(_target_hands(state))
    if not targets:
        return None

    selected = getattr(decision, "selected_plan", None)
    selected_probability = float(
        getattr(getattr(selected, "value", None), "clear_probability", 0.0) or 0.0
    )
    thresholds = getattr(decision, "thresholds", None)
    tolerance = float(
        getattr(thresholds, "safe_clear_probability_tolerance", 0.0) or 0.0
    )
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)

    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS or _plan_hand(policy, state, plan) not in targets:
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


def _play_targets_engine(policy, state, action) -> tuple[bool, tuple[str, ...], str]:
    targets = _target_hands(state)
    if action.name != PLAY_CARDS or not targets:
        return False, targets, ""
    rules = hand_rules_for_state(state)
    hand = _normalize(
        policy._hand_evaluator.evaluate(list(action.cards), rules=rules).value
    )
    return hand in set(targets), targets, hand


def _target_hand_strategy_fit(policy, state, action) -> tuple[float, tuple[str, ...]]:
    """Return Runner/To Do List candidate evidence for canonical D1 ranking."""
    matches, targets, hand = _play_targets_engine(policy, state, action)
    if not matches:
        return 0.0, ()
    return (
        TARGET_HAND_FIT,
        (
            f"target-hand engine evidence: {hand} matches {','.join(targets)}",
            "Runner/To Do List fit is consulted only inside canonical D1 safe/equivalent candidate ranking",
        ),
    )
