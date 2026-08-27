from __future__ import annotations

from time import perf_counter

from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


BOOTSTRAP_MAX_SECONDS = 1.50
BOOTSTRAP_BUDGET_FRACTION = 0.25
BOOTSTRAP_MIN_TOTAL_BUDGET_SECONDS = 0.05


def install_safe_pace_timeout_patch() -> None:
    if getattr(LiveHandActionDecisionEngine, "_safe_pace_timeout_installed", False):
        return

    original_decide = LiveHandActionDecisionEngine.decide

    def decide(self, state):
        # Before the adaptive horizon-2+ schedule can consume the whole wall-clock
        # budget, seed D1 with a bounded horizon-1 root comparison. The candidate
        # deadline patch gives this bootstrap a partial root beam instead of forcing
        # exhaustive root ranking. Time spent here is deducted from the ordinary
        # configured search budget, so this does not extend D1's total allowance.
        configured_budget = getattr(self, "max_search_seconds", None)
        if configured_budget is not None and float(configured_budget) > 0.0:
            configured_budget = float(configured_budget)

            # Tiny/expired hard-budget configurations are themselves a contract:
            # they must enter the original bounded timeout path immediately rather
            # than spending a synthetic minimum amount of time on bootstrap work.
            if configured_budget <= BOOTSTRAP_MIN_TOTAL_BUDGET_SECONDS:
                return original_decide(self, state)

            started = perf_counter()
            bootstrap_budget = min(
                BOOTSTRAP_MAX_SECONDS,
                configured_budget * BOOTSTRAP_BUDGET_FRACTION,
            )
            self._search_deadline = started + bootstrap_budget
            try:
                bootstrap_plans = self._rank_immediate_plans(state)
            except (PlannerSearchBudgetExceeded, AttributeError, RuntimeError, TypeError, ValueError):
                bootstrap_plans = []

            # PathAwareLiveHandActionDecisionEngine owns production timeout
            # authority. Feed the completed bootstrap into its canonical evidence
            # history instead of installing another timeout selector here.
            if bootstrap_plans and hasattr(self, "_adaptive_plan_history"):
                self._adaptive_plan_history.append(tuple(bootstrap_plans))

            elapsed = max(0.0, perf_counter() - started)
            remaining = configured_budget - elapsed
            if remaining <= 0.0:
                return self._structural_timeout_fallback(
                    state,
                    search_attempts=(),
                )

            self.max_search_seconds = remaining
            try:
                return original_decide(self, state)
            finally:
                self.max_search_seconds = configured_budget

        return original_decide(self, state)

    LiveHandActionDecisionEngine.decide = decide
    LiveHandActionDecisionEngine._safe_pace_timeout_installed = True
