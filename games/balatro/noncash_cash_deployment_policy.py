from __future__ import annotations

"""Spend excess cash on weak non-cash Red/White builds instead of hoarding it.

This layer runs after Build Health. It only converts END_SHOP into a bounded reroll
when the public build is materially weak, the reroll is affordable, and the current
run is not a realized Bull/Bootstraps or cash-growth strategy. It never predicts
hidden shop contents and never rerolls below a small emergency reserve.
"""

from dataclasses import replace

from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_arbiter import BuildAwareShopArbiter


_HEALTH = RuntimeBuildHealthEvaluator()
_CASH_JOKERS = frozenset({"bull", "bulljoker", "bootstraps", "bootstrapsjoker"})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    for value in (
        getattr(joker, "name", None),
        getattr(joker, "label", None),
        getattr(joker, "ability_name", None),
        type(joker).__name__,
    ):
        token = _normalize(value or "")
        if token:
            return token
    return ""


def _strategy_tracker(arbiter, state):
    try:
        policy = arbiter._joker_policy_for_state(state)
    except (AttributeError, TypeError, ValueError):
        return None
    planner = getattr(policy, "transition_planner", None)
    evaluator = getattr(planner, "evaluator", None)
    return getattr(evaluator, "strategy_tracker", None)


def cash_scaling_active(arbiter, state) -> bool:
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    if owned & _CASH_JOKERS:
        return True

    tracker = _strategy_tracker(arbiter, state)
    if tracker is None:
        return False
    try:
        resolution = tracker.observe(state)
    except (AttributeError, TypeError, ValueError):
        return False
    strategy_id = getattr(resolution, "dominant_strategy_id", None)
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        try:
            strategy_id = getter(resolution)
        except (AttributeError, TypeError, ValueError):
            pass
    return str(strategy_id or "") == "cash_growth"


def weak_build_for_cash_deployment(health) -> bool:
    return bool(
        getattr(health, "scaling_deficit", False)
        or float(getattr(health, "survival", 100.0)) < 75.0
        or float(getattr(health, "immediate", 100.0)) < 70.0
    )


def deployment_reserve(ante: int) -> int:
    return 3 if int(ante) <= 2 else 5


def deployment_reroll_limit(money: int) -> int:
    return 2 if int(money) >= 25 else 1


def install_noncash_cash_deployment_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_noncash_cash_deployment_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        result = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.action.name != END_SHOP or reroll_cost is None:
            return result

        try:
            cost = int(reroll_cost)
        except (TypeError, ValueError):
            return result
        if cost <= 0 or cost > 8:
            return result
        if cash_scaling_active(self, state):
            return result

        tracker = _strategy_tracker(self, state)
        health = _HEALTH.evaluate(state, strategy_tracker=tracker)
        if not weak_build_for_cash_deployment(health):
            return result

        money = max(0, int(getattr(state, "money", 0) or 0))
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        reserve = deployment_reserve(ante)
        if money - cost < reserve:
            return result

        signature = (
            ante,
            int(getattr(state, "round", getattr(state, "round_num", 0)) or 0),
        )
        previous_signature = getattr(self, "_noncash_cash_deployment_signature", None)
        if previous_signature != signature:
            self._noncash_cash_deployment_signature = signature
            self._noncash_cash_deployment_count = 0

        count = int(getattr(self, "_noncash_cash_deployment_count", 0) or 0)
        limit = deployment_reroll_limit(money)
        if count >= limit:
            return result
        self._noncash_cash_deployment_count = count + 1

        reason = (
            "scaling deficit"
            if bool(getattr(health, "scaling_deficit", False))
            else "survival/immediate inadequacy"
        )
        return replace(
            result,
            action=BalatroAction(REFRESH_SHOP),
            source="NONCASH_CASH_DEPLOYMENT",
            normalized_gain=max(0.001, float(getattr(result, "normalized_gain", 0.0) or 0.0)),
            rationale=(
                f"weak non-cash build: deploy excess money instead of ending shop ({reason})",
                f"cash ${money}; reroll ${cost}; post-reroll reserve ${money - cost} >= ${reserve}",
                f"bounded deployment reroll {count + 1}/{limit}",
                f"Build Health survival={float(getattr(health, 'survival', 0.0)):.1f} immediate={float(getattr(health, 'immediate', 0.0)):.1f} scaling={float(getattr(health, 'scaling', 0.0)):.1f}",
                "Bull/Bootstraps/cash-growth runs are explicitly exempt so money remains scoring power",
                *result.rationale,
            ),
        )

    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._noncash_cash_deployment_installed = True
