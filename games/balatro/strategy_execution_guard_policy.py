from __future__ import annotations

"""Within-Play execution refinement for realized strategy engines.

Canonical D1 survival owns the Play/Discard action class. Realized hand-repetition
remains candidate-specific evidence and may refine only an already-selected PLAY.
No-discard realization is action-class evidence only: once canonical D1 selected a
PLAY, every PLAY already preserves that mechanic, so it must not run a second PLAY
selector.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


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
    """Compatibility helper retained for existing tests/callers."""
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return {"bannerjoker", "delayedgratificationjoker"}.issubset(owned)


def _realized_no_discard_engine(state) -> bool:
    if not _realized_bond(state, "no_discard"):
        return False
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return bool(
        owned
        & {
            "greenjoker",
            "delayedgratificationjoker",
            "bannerjoker",
        }
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


def _hand_key(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return _normalize(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    )


def _played_this_round(state) -> set[str]:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        counts = getattr(state, "hand_play_counts_this_round", None)
    if not isinstance(counts, dict):
        return set()
    return {_normalize(name) for name, count in counts.items() if int(count or 0) > 0}


def _safe_repeat_play(policy, state, plans, decision):
    """Return a safe repeated PLAY without changing the canonical action class."""
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


def install_strategy_execution_guard_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_strategy_execution_guard_policy_installed",
        False,
    ):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)

        if decision.action.name == DISCARD_CARDS:
            notes = []
            if _realized_no_discard_engine(state):
                notes.append(
                    "realized no_discard engine observed, but canonical D1 selected DISCARD; strategy evidence cannot change the finalized action class"
                )
            if _realized_bond(state, "hand_repetition"):
                notes.append(
                    "realized hand_repetition engine observed, but canonical D1 selected DISCARD; repetition evidence cannot change the finalized action class"
                )
            if notes:
                return replace(decision, rationale=(*decision.rationale, *notes))
            return decision

        if decision.action.name != PLAY_CARDS:
            return decision

        # No-discard realization does not select among PLAY candidates: every PLAY
        # already preserves the mechanic. Canonical D1 strategy-safe pace ranking
        # therefore remains authoritative without another no-discard reselector.
        repeat = _safe_repeat_play(self, state, plans, decision)
        if repeat is not None:
            probability, score, plan = repeat
            if getattr(decision.action, "cards", None) != getattr(plan.action, "cards", None):
                pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
                pace_ratio = score / pace_target if pace_target > 0.0 else float("inf")
                decision = replace(
                    decision,
                    action=plan.action,
                    selected_plan=plan,
                    selected_immediate_score=score,
                    selected_pace_ratio=pace_ratio,
                    selected_fallback_value=None,
                    confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), probability),
                    rationale=(
                        *decision.rationale,
                        "realized hand_repetition engine: within-PLAY refinement prefers a previously played hand on a survival-equivalent pace-qualified line",
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._strategy_execution_guard_policy_installed = True
