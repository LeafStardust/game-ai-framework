from __future__ import annotations

"""D1 safeguards derived from the 10-attempt Red/White calibration batch."""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_RECOVERY,
    LiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


BOSS_PROJECTION_SAFETY_MARGIN = 1.05


def _boss_active(state) -> bool:
    boss_name = str(getattr(state, "boss_name", "") or "")
    blind_type = str(getattr(state, "blind_type", "") or "").upper()
    return bool(boss_name) or blind_type == "BOSS"


def _projected_score(policy, state, plan) -> float:
    if plan.action.name != PLAY_CARDS:
        return 0.0
    return float(policy.evaluator.project_play(state, plan.action).expected_hand_score)


def _best_completed_clear_attempt(search_attempts, floor: float):
    completed = [
        attempt
        for attempt in search_attempts
        if not bool(getattr(attempt, "budget_exceeded", False))
        and getattr(attempt, "best_action", None) is not None
        and getattr(attempt, "best_clear_probability", None) is not None
        and float(attempt.best_clear_probability) >= floor
    ]
    if not completed:
        return None
    return max(
        completed,
        key=lambda attempt: (
            float(attempt.best_clear_probability or 0.0),
            int(getattr(attempt, "horizon", 0) or 0),
            float(getattr(attempt, "best_expected_score", 0.0) or 0.0),
        ),
    )


def install_d1_log_resilience_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_d1_log_resilience_installed", False):
        return

    # Boss scoring has enough special-case behavior that a raw exact flag is not
    # sufficient proof of a guaranteed clear. Force the normal confirmation path
    # unless the decision engine has independently supplied confirmed_clear_path.
    original_policy_decide = StrategyAwareLiveHandActionPolicy.decide

    def policy_decide(self, state, plans, **kwargs):
        supplied = tuple(plans)
        confirmed = kwargs.get("confirmed_clear_path")
        boss_unconfirmed = _boss_active(state) and confirmed is None
        if boss_unconfirmed:
            supplied = tuple(
                replace(plan, exact=False) if bool(getattr(plan, "exact", False)) else plan
                for plan in supplied
            )

        decision = original_policy_decide(self, state, supplied, **kwargs)
        attempts = tuple(kwargs.get("search_attempts", ()) or ())
        best_completed = _best_completed_clear_attempt(
            attempts,
            float(self.thresholds.clear_path_probability_floor),
        )
        timed_out_later = any(
            bool(getattr(attempt, "budget_exceeded", False))
            for attempt in attempts
        )

        # A later confirmation timeout must never erase a completed adaptive clear
        # result. Re-identify the most plausible root action from the supplied
        # candidates using the completed attempt's action family + projected score.
        if (
            decision.mode == PACE_RECOVERY
            and timed_out_later
            and best_completed is not None
        ):
            expected = float(getattr(best_completed, "best_expected_score", 0.0) or 0.0)
            candidates = [
                plan
                for plan in supplied
                if plan.action.name == best_completed.best_action
            ]
            if candidates:
                selected = min(
                    candidates,
                    key=lambda plan: abs(_projected_score(self, state, plan) - expected),
                )
                upgraded_value = replace(
                    selected.value,
                    clear_probability=max(
                        float(selected.value.clear_probability),
                        float(best_completed.best_clear_probability),
                    ),
                )
                selected = replace(selected, value=upgraded_value, exact=False)
                replacement_plans = tuple(
                    selected if plan.action == selected.action else plan
                    for plan in supplied
                )
                rescued = original_policy_decide(
                    self,
                    state,
                    replacement_plans,
                    search_attempts=attempts,
                    confirmed_clear_path=selected,
                    setup_discard_consensus=bool(
                        kwargs.get("setup_discard_consensus", False)
                    ),
                )
                decision = replace(
                    rescued,
                    confidence=min(float(rescued.confidence), 0.95),
                    rationale=(
                        "completed adaptive clear result preserved after a later search/confirmation timeout",
                        f"preserved horizon={best_completed.horizon} clear_probability={float(best_completed.best_clear_probability):.3f}",
                        *rescued.rationale,
                    ),
                )

        if boss_unconfirmed and decision.mode == CLEAR_PATH:
            decision = replace(
                decision,
                confidence=min(float(decision.confidence), 0.95),
                rationale=(
                    "boss projection exactness is treated as model-dependent until independently confirmed",
                    *decision.rationale,
                ),
            )

        # The batch contained a projected 22,212/23,145 clear against a 22,000 boss
        # that actually finished at 21,522. A barely pace-qualified boss play is
        # therefore not treated as deterministic truth. When a legal discard still
        # exists, demand 5% projected headroom before consuming that hand.
        ratio = getattr(decision, "selected_pace_ratio", None)
        if (
            _boss_active(state)
            and decision.mode != CLEAR_PATH
            and decision.action.name == PLAY_CARDS
            and ratio is not None
            and 1.0 <= float(ratio) < BOSS_PROJECTION_SAFETY_MARGIN
            and int(getattr(state, "discards_remaining", 0) or 0) > 0
        ):
            discards = [plan for plan in supplied if plan.action.name == DISCARD_CARDS]
            if discards:
                selected = max(
                    discards,
                    key=lambda plan: (
                        float(self.evaluator.evaluate(state, plan.action)),
                        self._within_type_key(plan),
                    ),
                )
                decision = replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=float(
                        self.evaluator.evaluate(state, selected.action)
                    ),
                    confidence=min(float(decision.confidence), 0.90),
                    rationale=(
                        f"boss projected pace ratio={float(ratio):.3f} is below the {BOSS_PROJECTION_SAFETY_MARGIN:.2f} model-uncertainty margin",
                        "a legal discard remains; seek a safer hand instead of trusting a marginal score projection",
                        *decision.rationale,
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = policy_decide

    # Reserve the tail of the configured D1 budget for deterministic pace/survival
    # fallback. The public configured budget remains unchanged after the call.
    original_engine_decide = LiveHandActionDecisionEngine.decide

    def engine_decide(self, state):
        configured = self.max_search_seconds
        if configured is None or float(configured) <= 1.25:
            return original_engine_decide(self, state)
        reserve = min(1.0, max(0.50, float(configured) * 0.125))
        try:
            self.max_search_seconds = max(0.25, float(configured) - reserve)
            decision = original_engine_decide(self, state)
        finally:
            self.max_search_seconds = configured
        return replace(
            decision,
            rationale=(
                *decision.rationale,
                f"D1 deterministic fallback reserve={reserve:.3f}s from configured {float(configured):.3f}s budget",
            ),
        )

    LiveHandActionDecisionEngine.decide = engine_decide
    StrategyAwareLiveHandActionPolicy._d1_log_resilience_installed = True
