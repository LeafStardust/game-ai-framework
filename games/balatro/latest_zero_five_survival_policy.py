from __future__ import annotations

"""Survival calibration from the 2026-08-21 0/5 Red/White batch.

Two runs died before Ante 3 after exhausting every discard.  The composed safe-
pace policy intentionally discards whenever no current play reaches full per-hand
pace.  That rule is appropriate once scoring requirements accelerate, but it is too
binary in the opening game: a strong near-pace hand can be worth banking because it
reduces the remaining blind requirement while preserving future draws.

This layer is deliberately narrow.  It only overrides a DISCARD recommendation in
Ante 1-2 when the best legal current play already reaches 75% of required pace.
Later antes retain the stricter safe-pace rule unchanged.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy


OPENING_BANK_PACE_RATIO_FLOOR = 0.75


def should_bank_opening_play(
    *,
    ante: int,
    best_pace_ratio: float,
    discards_remaining: int,
) -> bool:
    """Return whether a near-pace opening hand should be banked instead of discarded."""
    return (
        int(ante) <= 2
        and int(discards_remaining) > 0
        and float(best_pace_ratio) >= OPENING_BANK_PACE_RATIO_FLOOR
        and float(best_pace_ratio) < 1.0
    )


def install_latest_zero_five_survival_policy() -> None:
    if getattr(LiveHandActionPolicy, "_latest_zero_five_survival_installed", False):
        return

    original_decide = LiveHandActionPolicy.decide

    def decide(
        self,
        state,
        plans,
        *,
        search_attempts=(),
        confirmed_clear_path=None,
        setup_discard_consensus=False,
    ):
        plans = tuple(plans)
        decision = original_decide(
            self,
            state,
            plans,
            search_attempts=search_attempts,
            confirmed_clear_path=confirmed_clear_path,
            setup_discard_consensus=setup_discard_consensus,
        )
        if str(getattr(decision.action, "name", "")) != DISCARD_CARDS:
            return decision

        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        if not plays:
            return decision

        pace_target = float(self._pace_target(state))
        projections = {
            id(plan): self.evaluator.project_play(state, plan.action)
            for plan in plays
        }
        scores = {
            id(plan): float(projections[id(plan)].expected_hand_score)
            for plan in plays
        }
        best_play = max(plays, key=lambda plan: scores[id(plan)])
        best_score = scores[id(best_play)]
        best_ratio = float(self._pace_ratio(best_score, pace_target))
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        discards_remaining = max(
            0,
            int(getattr(state, "discards_remaining", 0) or 0),
        )
        if not should_bank_opening_play(
            ante=ante,
            best_pace_ratio=best_ratio,
            discards_remaining=discards_remaining,
        ):
            return decision

        best_discard = max(
            (plan for plan in plans if plan.action.name == DISCARD_CARDS),
            key=self._within_type_key,
            default=None,
        )
        return self._decision(
            mode=PACE_PLAY,
            selected=best_play,
            best_play=best_play,
            best_discard=best_discard,
            pace_target=pace_target,
            best_play_immediate_score=best_score,
            best_play_pace_ratio=best_ratio,
            selected_immediate_score=best_score,
            selected_pace_ratio=best_ratio,
            selected_fallback_value=None,
            clear_path_candidates=0,
            sampled_clear_path_confirmed=False,
            setup_discard_consensus=False,
            confidence=max(0.50, min(0.90, best_ratio)),
            rationale=(
                "0/5 opening-survival calibration: bank a strong near-pace hand instead of spending another discard",
                f"Ante {ante} projected pace ratio={best_ratio:.3f} >= opening bank floor={OPENING_BANK_PACE_RATIO_FLOOR:.3f}",
                "this exception applies only in Antes 1-2; later blinds keep the strict safe-pace discard rule",
            ),
            plans=plans,
            search_attempts=search_attempts,
        )

    LiveHandActionPolicy.decide = decide
    LiveHandActionPolicy._latest_zero_five_survival_installed = True
