from __future__ import annotations

from time import perf_counter

from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


BOOTSTRAP_MAX_SECONDS = 1.50
BOOTSTRAP_BUDGET_FRACTION = 0.25


def install_safe_pace_timeout_patch() -> None:
    if getattr(LiveHandActionDecisionEngine, "_safe_pace_timeout_installed", False):
        return

    original_decide = LiveHandActionDecisionEngine.decide
    original_rank_plans = LiveHandActionDecisionEngine.rank_plans
    original_fallback = LiveHandActionDecisionEngine._structural_timeout_fallback

    def decide(self, state):
        # Completed search evidence is valid only for the current settled hand.
        # Reset it before every top-level D1 decision so a later checkpoint can
        # never inherit plans from an earlier hand.
        self._safe_pace_completed_root_plans = ()

        # Before the adaptive horizon-2+ schedule can consume the whole wall-clock
        # budget, seed D1 with a bounded horizon-1 root comparison. The candidate
        # deadline patch gives this bootstrap a partial root beam instead of forcing
        # exhaustive root ranking. Time spent here is deducted from the ordinary
        # configured search budget, so this does not extend D1's total allowance.
        configured_budget = getattr(self, "max_search_seconds", None)
        if configured_budget is not None and float(configured_budget) > 0.0:
            configured_budget = float(configured_budget)
            started = perf_counter()
            bootstrap_budget = min(
                BOOTSTRAP_MAX_SECONDS,
                max(0.05, configured_budget * BOOTSTRAP_BUDGET_FRACTION),
            )
            self._search_deadline = started + bootstrap_budget
            try:
                bootstrap_plans = self._rank_immediate_plans(state)
            except (PlannerSearchBudgetExceeded, AttributeError, RuntimeError, TypeError, ValueError):
                bootstrap_plans = []
            if bootstrap_plans:
                self._safe_pace_completed_root_plans = tuple(bootstrap_plans)

            elapsed = max(0.0, perf_counter() - started)
            remaining = max(0.05, configured_budget - elapsed)
            self.max_search_seconds = remaining
            try:
                return original_decide(self, state)
            finally:
                self.max_search_seconds = configured_budget

        return original_decide(self, state)

    def rank_plans(self, state, *, planner=None):
        plans = original_rank_plans(self, state, planner=planner)
        active_planner = planner or self.planner

        # Confirmation searches deliberately constrain the root to one action.
        # Do not let that narrower sample replace the broader completed root set
        # that remains our best bounded fallback if a later/deeper pass times out.
        if (
            plans
            and getattr(active_planner, "_confirmation_root_action", None) is None
        ):
            self._safe_pace_completed_root_plans = tuple(plans)
        return plans

    def fallback(self, state, *, search_attempts):
        completed = tuple(
            getattr(self, "_safe_pace_completed_root_plans", ()) or ()
        )
        if completed:
            # A deeper search timing out is not evidence that the earlier completed
            # search became invalid. Reuse that bounded work instead of throwing it
            # away and manufacturing an unsearched structural action. The normal D1
            # policy still decides between the completed Play/Discard candidates.
            try:
                decision = self.policy.decide(
                    state,
                    completed,
                    search_attempts=search_attempts,
                    setup_discard_consensus=False,
                )
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
                decision = None
            if decision is not None:
                rationale = tuple(getattr(decision, "rationale", ()) or ())
                try:
                    from dataclasses import replace

                    return replace(
                        decision,
                        rationale=(
                            "D1 wall-clock budget exhausted after at least one bounded root pass completed",
                            "reused the strongest completed root search instead of discarding bounded evidence",
                            *rationale,
                        ),
                    )
                except (TypeError, ValueError):
                    # Lightweight fixtures are allowed in the policy tests. The
                    # decision itself is already valid even when it is not a dataclass.
                    return decision

        # Only a timeout before *any* bounded root pass completes reaches the original
        # structural Play fallback. A timeout alone never authorizes a fabricated discard.
        return original_fallback(self, state, search_attempts=search_attempts)

    LiveHandActionDecisionEngine.decide = decide
    LiveHandActionDecisionEngine.rank_plans = rank_plans
    LiveHandActionDecisionEngine._structural_timeout_fallback = fallback
    LiveHandActionDecisionEngine._safe_pace_timeout_installed = True
