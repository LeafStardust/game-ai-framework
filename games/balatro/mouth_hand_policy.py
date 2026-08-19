from __future__ import annotations

"""The Mouth first-hand lock policy for strategy-aware D1.

The Mouth allows only the first accepted poker-hand type to score for the rest of
that blind. Generic pace logic must therefore not casually lock the run into an
inferior off-strategy hand just because that hand happens to meet the immediate
pace floor.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.hand_action_policy import PACE_PLAY, PACE_RECOVERY
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


def _primary_hand_types(policy, state) -> tuple[str, ...]:
    resolution = policy.strategy_tracker.observe(state)
    strategy_id = resolution.dominant_strategy_id
    primary_getter = getattr(policy.strategy_tracker, "primary_strategy_id", None)
    if callable(primary_getter):
        strategy_id = primary_getter(resolution)
    if strategy_id is None:
        return ()
    return tuple(
        str(hand).upper()
        for hand in policy.strategy_tracker.primary_hands_for(strategy_id)
    )


def _hand_type(policy, plan) -> str:
    return str(
        policy._hand_evaluator.evaluate(list(plan.action.cards)).value
    ).upper()


def _projected_score(policy, state, plan) -> float:
    return float(
        policy.evaluator.project_play(state, plan.action).expected_hand_score
    )


def _replace_with_play(policy, state, decision, plan, *, rationale: tuple[str, ...]):
    score = _projected_score(policy, state, plan)
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
        confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 0.90),
        rationale=(*rationale, *decision.rationale),
    )


def _replace_with_discard(policy, state, decision, plan, *, rationale: tuple[str, ...]):
    value = float(policy.evaluator.evaluate(state, plan.action))
    return replace(
        decision,
        mode=PACE_RECOVERY,
        action=plan.action,
        selected_plan=plan,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=value,
        confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 0.90),
        rationale=(*rationale, *decision.rationale),
    )


def apply_mouth_first_hand_policy(policy, state, plans, decision):
    """Choose The Mouth's first accepted hand deliberately.

    Priority:
      1. Any immediate one-hand blind clear. The Mouth cannot matter afterwards.
      2. A currently playable hand type prescribed by the primary strategy; among
         those, lock the highest projected scoring hand.
      3. If the prescribed type is not currently playable and discards remain,
         discard toward it instead of locking an off-strategy hand.
      4. With no prescribed hand route (or no discards), lock the highest projected
         scoring legal hand under the actual current Joker/build projection.
    """
    if not _mouth_is_unlocked(state):
        return decision

    plans = tuple(plans)
    plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
    if not plays:
        return decision

    remaining_score = max(
        0.0,
        float(getattr(state, "blind_score", 0) or 0)
        - float(getattr(state, "score", 0) or 0),
    )
    scored_plays = tuple(
        (plan, _projected_score(policy, state, plan), _hand_type(policy, plan))
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
                f"The Mouth first-hand lock bypassed because {hand_type} immediately clears the blind ({score:.3f} projected)",
            ),
        )

    preferred = set(_primary_hand_types(policy, state))
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
                    f"The Mouth is not locked; primary strategy prescribes {','.join(sorted(preferred))}",
                    f"lock The Mouth to {hand_type}, the highest projected scoring available primary-strategy hand ({score:.3f})",
                    "do not let a merely pace-qualified off-strategy hand determine the entire boss blind",
                ),
            )

        discards = tuple(
            plan for plan in plans if plan.action.name == DISCARD_CARDS
        )
        if discards and int(getattr(state, "discards_remaining", 0) or 0) > 0:
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
                    f"The Mouth is not locked and primary strategy wants {','.join(sorted(preferred))}",
                    "no preferred hand type is currently playable; use a discard instead of locking an inferior hand type",
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
            "The Mouth is not locked and no playable primary-strategy hand is available",
            f"lock to the highest projected scoring legal hand: {hand_type} ({score:.3f})",
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
