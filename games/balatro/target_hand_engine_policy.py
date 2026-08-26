from __future__ import annotations

"""Final D1 execution for Jokers whose known mechanic targets a poker hand.

Balatro's Joker catalogue is finite and stable, so Joker mechanics are modeled
explicitly while the execution rule stays generic: if an owned engine rewards a
specific poker hand, prefer that hand whenever it is already survival-equivalent
and pace-qualified.  This prevents the strategy layer from owning Runner or a
stateful To Do List target while D1 never actually uses the mechanic.
"""

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.hand_action_policy import PACE_PLAY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


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


def install_target_hand_engine_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_target_hand_engine_policy_installed", False):
        return
    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)
        target = _safe_target_play(self, state, plans, decision)
        if target is None:
            return decision

        probability, score, plan = target
        if (
            decision.action.name == PLAY_CARDS
            and getattr(decision.action, "cards", None) == getattr(plan.action, "cards", None)
        ):
            return decision

        pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
        pace_ratio = score / pace_target if pace_target > 0.0 else float("inf")
        return replace(
            decision,
            mode=PACE_PLAY,
            action=plan.action,
            selected_plan=plan,
            selected_immediate_score=score,
            selected_pace_ratio=pace_ratio,
            selected_fallback_value=None,
            confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), probability),
            rationale=(
                "owned target-hand engine: prefer its poker hand on a survival-equivalent pace-qualified line",
                f"target hands={','.join(_target_hands(state))}",
                f"target-line clear probability={probability:.3f}",
                *decision.rationale,
            ),
        )

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._target_hand_engine_policy_installed = True
