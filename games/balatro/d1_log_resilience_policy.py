from __future__ import annotations

"""D1 safeguards derived from live Red/White calibration runs."""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_RECOVERY,
    LiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


BOSS_PROJECTION_SAFETY_MARGIN = 1.05
PROACTIVE_DISCARD_SCORE_MARGIN = 1.05


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


def _best_completed_scoring_attempt(search_attempts):
    """Keep the strongest completed adaptive recommendation, including DISCARD."""
    completed = [
        attempt
        for attempt in search_attempts
        if not bool(getattr(attempt, "budget_exceeded", False))
        and getattr(attempt, "best_action", None) is not None
        and getattr(attempt, "best_expected_score", None) is not None
    ]
    if not completed:
        return None
    return max(
        completed,
        key=lambda attempt: (
            int(getattr(attempt, "horizon", 0) or 0),
            float(getattr(attempt, "best_expected_score", 0.0) or 0.0),
            float(getattr(attempt, "best_clear_probability", 0.0) or 0.0),
        ),
    )


def _best_discard_plan(policy, state, supplied):
    discards = [plan for plan in supplied if plan.action.name == DISCARD_CARDS]
    if not discards:
        return None
    return max(
        discards,
        key=lambda plan: (
            float(policy.evaluator.evaluate(state, plan.action)),
            policy._strategy_fit(state, plan.action),
            policy._within_type_key(plan),
        ),
    )


def _discard_decision(policy, state, decision, selected, *, rationale):
    fallback = float(policy.evaluator.evaluate(state, selected.action))
    return replace(
        decision,
        mode=PACE_RECOVERY,
        action=selected.action,
        selected_plan=selected,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=fallback,
        confidence=max(0.55, min(float(decision.confidence), 0.92)),
        rationale=(
            *rationale,
            *decision.rationale,
        ),
    )


def install_d1_log_resilience_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_d1_log_resilience_installed", False):
        return

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
        best_completed_clear = _best_completed_clear_attempt(
            attempts,
            float(self.thresholds.clear_path_probability_floor),
        )
        best_completed_scoring = _best_completed_scoring_attempt(attempts)
        timed_out_later = any(
            bool(getattr(attempt, "budget_exceeded", False))
            for attempt in attempts
        )

        # Never trade away a credible immediate clear merely to chase a prettier hand.
        if decision.mode != CLEAR_PATH:
            discard_plan = _best_discard_plan(self, state, supplied)
            search_prefers_discard = bool(
                best_completed_scoring is not None
                and str(best_completed_scoring.best_action) == DISCARD_CARDS
            )
            expected_after_discard = (
                float(best_completed_scoring.best_expected_score or 0.0)
                if search_prefers_discard
                else 0.0
            )
            current_score = float(getattr(decision, "selected_immediate_score", 0.0) or 0.0)
            materially_better = bool(
                search_prefers_discard
                and (
                    current_score <= 0.0
                    or expected_after_discard
                    >= current_score * PROACTIVE_DISCARD_SCORE_MARGIN
                )
            )
            setup_consensus = bool(kwargs.get("setup_discard_consensus", False))

            # Pace is a survival signal, not a command to burn a hand. When completed
            # search says a discard produces a materially stronger scoring route, or
            # setup search independently agrees on discard, use the discard now.
            if (
                discard_plan is not None
                and int(getattr(state, "discards_remaining", 0) or 0) > 0
                and (materially_better or setup_consensus)
            ):
                reason = (
                    "completed adaptive search prefers DISCARD to pursue a materially higher-scoring hand"
                    if materially_better
                    else "independent setup search agrees that DISCARD improves the next scoring hand"
                )
                decision = _discard_decision(
                    self,
                    state,
                    decision,
                    discard_plan,
                    rationale=(
                        reason,
                        f"projected next-hand score={expected_after_discard:.3f}; current immediate score={current_score:.3f}",
                        "pace-qualified PLAY is no longer authoritative when a legal discard has stronger scoring evidence",
                    ),
                )

            # A timeout may not erase a completed DISCARD recommendation. This is the
            # exact regression observed in the uploaded run: adaptive search selected
            # DISCARD, the next stage hit the wall clock, and fallback played High Card.
            elif (
                discard_plan is not None
                and search_prefers_discard
                and timed_out_later
                and int(getattr(state, "discards_remaining", 0) or 0) > 0
            ):
                decision = _discard_decision(
                    self,
                    state,
                    decision,
                    discard_plan,
                    rationale=(
                        "preserved completed adaptive DISCARD recommendation after a later search timeout",
                        f"preserved horizon={best_completed_scoring.horizon} projected next-hand score={expected_after_discard:.3f}",
                    ),
                )

        # A later confirmation timeout must never erase a completed adaptive clear.
        if (
            decision.mode == PACE_RECOVERY
            and timed_out_later
            and best_completed_clear is not None
            and str(best_completed_clear.best_action) != DISCARD_CARDS
        ):
            expected = float(getattr(best_completed_clear, "best_expected_score", 0.0) or 0.0)
            candidates = [
                plan for plan in supplied if plan.action.name == best_completed_clear.best_action
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
                        float(best_completed_clear.best_clear_probability),
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
                    setup_discard_consensus=bool(kwargs.get("setup_discard_consensus", False)),
                )
                decision = replace(
                    rescued,
                    confidence=min(float(rescued.confidence), 0.95),
                    rationale=(
                        "completed adaptive clear result preserved after a later search/confirmation timeout",
                        f"preserved horizon={best_completed_clear.horizon} clear_probability={float(best_completed_clear.best_clear_probability):.3f}",
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

        ratio = getattr(decision, "selected_pace_ratio", None)
        if (
            _boss_active(state)
            and decision.mode != CLEAR_PATH
            and decision.action.name == PLAY_CARDS
            and ratio is not None
            and 1.0 <= float(ratio) < BOSS_PROJECTION_SAFETY_MARGIN
            and int(getattr(state, "discards_remaining", 0) or 0) > 0
        ):
            selected = _best_discard_plan(self, state, supplied)
            if selected is not None:
                decision = _discard_decision(
                    self,
                    state,
                    decision,
                    selected,
                    rationale=(
                        f"boss projected pace ratio={float(ratio):.3f} is below the {BOSS_PROJECTION_SAFETY_MARGIN:.2f} model-uncertainty margin",
                        "a legal discard remains; seek a safer hand instead of trusting a marginal score projection",
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = policy_decide

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
