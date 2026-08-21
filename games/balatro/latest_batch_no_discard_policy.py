from __future__ import annotations

"""Narrow no-discard optimization from the 2026-08-21 Red/White batch.

Attempt 1 reached Ante 5 with Banner + Delayed Gratification, then spent every
available discard. Before the first discard this pair is a realized coherent
package: preserving discards keeps Banner's chips at full strength and preserves
Delayed Gratification's end-of-round payout. This policy does not forbid discards;
it only avoids the first discard when an immediately playable hand already meets
D1's own current pace target.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import PACE_PLAY
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


def realized_banner_delayed_no_discard(state) -> bool:
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return {"bannerjoker", "delayedgratificationjoker"}.issubset(owned)


def _safe_pace_play(policy, state, plans, decision):
    """Return the best play already meeting D1's own pace target, if one exists."""
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    if pace_target <= 0.0:
        return None

    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS:
            continue
        score = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        if score >= pace_target:
            candidates.append((score, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[0],
            policy._strategy_fit(state, item[1].action)[0],
            policy._within_type_key(item[1]),
        ),
    )


def install_latest_batch_no_discard_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_latest_batch_no_discard_policy_installed",
        False,
    ):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        decision = original_decide(self, state, plans, **kwargs)
        if decision.action.name != DISCARD_CARDS:
            return decision
        if not realized_banner_delayed_no_discard(state):
            return decision
        if int(getattr(state, "discards_used", 0) or 0) != 0:
            return decision

        safe = _safe_pace_play(self, state, plans, decision)
        if safe is None:
            # Survival takes precedence. If no current play meets the existing
            # pace target, retain the underlying D1 discard decision unchanged.
            return decision

        score, plan = safe
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
            rationale=(
                "realized Banner + Delayed Gratification no-discard package: preserve the first discard when a play already meets D1 pace",
                f"selected play projects {score:.3f} against pace target {pace_target:.3f}",
                "survival still overrides this rule whenever no current play meets pace",
                *decision.rationale,
            ),
        )

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._latest_batch_no_discard_policy_installed = True
