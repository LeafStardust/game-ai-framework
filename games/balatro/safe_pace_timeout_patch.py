from __future__ import annotations

from games.balatro.actions import DISCARD_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import PACE_RECOVERY, LiveHandActionDecisionEngine


def install_safe_pace_timeout_patch() -> None:
    if getattr(LiveHandActionDecisionEngine, "_safe_pace_timeout_installed", False):
        return

    original = LiveHandActionDecisionEngine._structural_timeout_fallback

    def fallback(self, state, *, search_attempts):
        planner = self.planner
        planner._require_state(state)
        pace_target = self.policy._pace_target(state)

        # The structural path must be cheap: no Joker-aware projections after the
        # wall-clock deadline. Production planners expose a discard generator; tiny
        # test/fake planners may not, in which case retain the original bounded
        # structural PLAY fallback rather than assuming an unavailable interface.
        generator = getattr(getattr(planner, "action_generator", None), "generate_discard_actions", None)
        if (
            int(getattr(state, "discards_remaining", 0) or 0) > 0
            and callable(generator)
        ):
            discards = list(generator(state))
            if discards:
                action = discards[0]
                value = LiveBlindPlanValue(
                    clear_probability=0.0,
                    expected_progress=0.0,
                    expected_score=float(getattr(state, "score", 0) or 0),
                    expected_hands_remaining=float(getattr(state, "hands_remaining", 0) or 0),
                    expected_discards_remaining=float(
                        max(0, int(getattr(state, "discards_remaining", 0) or 0) - 1)
                    ),
                )
                plan = LiveBlindPlan(
                    action=action,
                    value=value,
                    horizon=1,
                    exact=False,
                    candidate_count=len(discards),
                )
                return self.policy._decision(
                    mode=PACE_RECOVERY,
                    selected=plan,
                    best_play=plan,
                    best_discard=plan,
                    pace_target=pace_target,
                    best_play_immediate_score=0.0,
                    best_play_pace_ratio=0.0,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=None,
                    clear_path_candidates=0,
                    sampled_clear_path_confirmed=False,
                    setup_discard_consensus=False,
                    confidence=0.50,
                    rationale=(
                        "D1 wall-clock budget exhausted",
                        "safe-pace timeout invariant: a legal discard remains, so do not burn an under-pace scoring hand",
                        "take only this discard, then re-observe and replan",
                    ),
                    plans=(plan,),
                    search_attempts=search_attempts,
                )

        # With no observable discard generator/choice available, retain the
        # original bounded structural Play. This keeps the timeout path total and
        # avoids entering any unbounded immediate recovery after expiry.
        return original(self, state, search_attempts=search_attempts)

    LiveHandActionDecisionEngine._structural_timeout_fallback = fallback
    LiveHandActionDecisionEngine._safe_pace_timeout_installed = True
