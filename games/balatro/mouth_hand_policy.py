from __future__ import annotations

"""The Mouth first-hand lock policy for Bond-aware D1.

The Mouth allows only the first accepted poker-hand type to score for the rest of
that blind. Canonical D1 survival owns the Play/Discard action class; this policy
may only refine the candidate within the already-authorized class.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _mouth_is_unlocked(state) -> bool:
    if str(getattr(state, "boss_name", "") or "") != "The Mouth":
        return False
    if boss_blind_disabled_by_owned_jokers(state):
        return False
    if getattr(state, "boss_blind_only_hand", None) is not None:
        return False
    counts = getattr(state, "round_hand_play_counts", None)
    if isinstance(counts, dict) and any(int(value or 0) > 0 for value in counts.values()):
        return False
    return True


def _bond_hand_types(policy, state) -> tuple[str, ...]:
    """Return all developed hand targets selected by canonical Bond composition."""
    intents = policy._hand_bond_intents(state)
    return tuple(sorted({str(target).upper() for target, weight, _ in intents if weight > 0.0}))


def _hand_type(policy, state, plan) -> str:
    return str(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=hand_rules_for_state(state),
        ).value
    ).upper()


def _projected_score(policy, state, plan) -> float:
    return float(policy.evaluator.project_play(state, plan.action).expected_hand_score)


def _replace_with_play(policy, state, decision, plan, *, rationale: tuple[str, ...]):
    score = _projected_score(policy, state, plan)
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    pace_ratio = score / pace_target if pace_target > 0.0 else float("inf")
    return replace(
        decision,
        action=plan.action,
        selected_plan=plan,
        selected_immediate_score=score,
        selected_pace_ratio=pace_ratio,
        selected_fallback_value=None,
        confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 0.90),
        rationale=(*rationale, *decision.rationale),
    )


def _replace_with_discard(policy, state, decision, plan, *, rationale: tuple[str, ...]):
    value = float(policy.evaluator.evaluate(state, plan.action))
    return replace(
        decision,
        action=plan.action,
        selected_plan=plan,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=value,
        confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 0.90),
        rationale=(*rationale, *decision.rationale),
    )


def apply_mouth_first_hand_policy(policy, state, plans, decision):
    """Refine The Mouth's first-hand choice without changing D1 action class."""
    if not _mouth_is_unlocked(state):
        return decision

    plans = tuple(plans)
    preferred = set(_bond_hand_types(policy, state))

    if decision.action.name == DISCARD_CARDS:
        discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
        if not discards:
            return decision
        if not preferred:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "The Mouth is unlocked, but canonical D1 selected DISCARD and no developed Bond hand target requires a different within-DISCARD refinement",
                ),
            )
        plan = max(
            discards,
            key=lambda candidate: (
                policy._strategy_fit(state, candidate.action)[0],
                float(policy.evaluator.evaluate(state, candidate.action)),
                policy._within_type_key(candidate),
            ),
        )
        return _replace_with_discard(
            policy,
            state,
            decision,
            plan,
            rationale=(
                f"The Mouth is not locked and developed Bonds target {','.join(sorted(preferred))}",
                "canonical D1 already selected DISCARD; shape that discard toward the Bond target without changing action class",
            ),
        )

    if decision.action.name != PLAY_CARDS:
        return decision

    plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
    if not plays:
        return decision

    remaining_score = max(
        0.0,
        float(getattr(state, "blind_score", 0) or 0)
        - float(getattr(state, "score", 0) or 0),
    )
    scored_plays = tuple(
        (plan, _projected_score(policy, state, plan), _hand_type(policy, state, plan))
        for plan in plays
    )

    one_shot = [entry for entry in scored_plays if entry[1] >= remaining_score > 0.0]
    if one_shot:
        plan, score, hand_type = max(
            one_shot,
            key=lambda entry: (
                entry[1],
                policy._strategy_fit(state, entry[0].action)[0],
                policy._within_type_key(entry[0]),
            ),
        )
        return _replace_with_play(
            policy,
            state,
            decision,
            plan,
            rationale=(
                f"The Mouth first-hand lock is irrelevant after an immediate clear; select {hand_type} ({score:.3f} projected) within canonical PLAY",
            ),
        )

    if preferred:
        matching = [entry for entry in scored_plays if entry[2] in preferred]
        if matching:
            plan, score, hand_type = max(
                matching,
                key=lambda entry: (
                    entry[1],
                    policy._strategy_fit(state, entry[0].action)[0],
                    policy._within_type_key(entry[0]),
                ),
            )
            return _replace_with_play(
                policy,
                state,
                decision,
                plan,
                rationale=(
                    f"The Mouth is not locked; developed Bonds target {','.join(sorted(preferred))}",
                    f"within canonical PLAY, lock The Mouth to {hand_type}, the strongest available Bond-targeted hand ({score:.3f})",
                ),
            )
        return replace(
            decision,
            rationale=(
                *decision.rationale,
                f"The Mouth is not locked and developed Bonds target {','.join(sorted(preferred))}, but no target hand is playable; canonical PLAY remains authoritative rather than switching to DISCARD here",
            ),
        )

    plan, score, hand_type = max(
        scored_plays,
        key=lambda entry: (
            entry[1],
            policy._strategy_fit(state, entry[0].action)[0],
            policy._within_type_key(entry[0]),
        ),
    )
    return _replace_with_play(
        policy,
        state,
        decision,
        plan,
        rationale=(
            "The Mouth is not locked and no developed Bond hand target is currently playable",
            f"within canonical PLAY, lock to the highest projected scoring legal hand: {hand_type} ({score:.3f})",
        ),
    )


def install_mouth_first_hand_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_mouth_policy_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        decision = original_decide(self, state, plans, **kwargs)
        return apply_mouth_first_hand_policy(self, state, plans, decision)

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._mouth_policy_installed = True
