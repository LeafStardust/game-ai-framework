from __future__ import annotations

"""Diagnostic-only substage timing for one D14 SHOP arbitration.

The profiler is intentionally observational. It wraps the existing D14 parent and
child methods without changing inputs, outputs, thresholds, budgets, or authority.
A ContextVar keeps concurrent/test calls isolated and exposes only the most recent
completed D14 profile to the live-runner diagnostic layer.
"""

from contextvars import ContextVar
from time import perf_counter

from games.balatro.reroll_joker_expectation_policy import (
    RerollJokerExpectationEvaluator,
)
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy


_ACTIVE_PROFILE: ContextVar[dict[str, float | int] | None] = ContextVar(
    "balatro_shop_d14_active_profile",
    default=None,
)
_LAST_PROFILE: ContextVar[dict[str, float | int] | None] = ContextVar(
    "balatro_shop_d14_last_profile",
    default=None,
)

# These buckets are disjoint direct children of D14. ``deterministic`` is excluded
# because BalatroShopPolicy.rank_actions can also execute inside reroll evaluation;
# it remains visible as an overlapping informational metric.
_TOP_LEVEL_STAGES = (
    "joker",
    "consumable",
    "booster",
    "bond_pair",
    "reroll",
)


def _record_stage(name: str, call, *args, **kwargs):
    profile = _ACTIVE_PROFILE.get()
    if profile is None:
        return call(*args, **kwargs)

    started = perf_counter()
    try:
        return call(*args, **kwargs)
    finally:
        elapsed = perf_counter() - started
        seconds_key = f"{name}_seconds"
        calls_key = f"{name}_calls"
        profile[seconds_key] = float(profile.get(seconds_key, 0.0)) + elapsed
        profile[calls_key] = int(profile.get(calls_key, 0)) + 1


def clear_shop_policy_latency_profile() -> None:
    _LAST_PROFILE.set(None)


def consume_shop_policy_latency_note() -> str | None:
    profile = _LAST_PROFILE.get()
    _LAST_PROFILE.set(None)
    if not isinstance(profile, dict):
        return None

    total = float(profile.get("total_seconds", 0.0))
    top_level = sum(
        float(profile.get(f"{name}_seconds", 0.0))
        for name in _TOP_LEVEL_STAGES
    )
    residual = max(0.0, total - top_level)
    return (
        "shop_d14_latency="
        f"total={total:.3f}s "
        f"deterministic={float(profile.get('deterministic_seconds', 0.0)):.3f}s "
        f"joker={float(profile.get('joker_seconds', 0.0)):.3f}s "
        f"consumable={float(profile.get('consumable_seconds', 0.0)):.3f}s "
        f"booster={float(profile.get('booster_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('booster_calls', 0))}calls "
        f"bond_pair={float(profile.get('bond_pair_seconds', 0.0)):.3f}s "
        f"reroll={float(profile.get('reroll_seconds', 0.0)):.3f}s "
        f"reroll_joker={float(profile.get('reroll_joker_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_joker_calls', 0))}calls "
        f"residual={residual:.3f}s"
    )


def install_shop_policy_latency_diagnostic() -> None:
    if getattr(BuildAwareShopArbiter, "_shop_policy_latency_diagnostic_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide
    original_rank_actions = BalatroShopPolicy.rank_actions
    original_best_joker = BuildAwareShopArbiter._best_joker_decision
    original_best_consumable = BuildAwareShopArbiter._best_consumable_decision
    original_best_bond_pair = BuildAwareShopArbiter._best_visible_bond_pair
    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend
    original_reroll_recommend = BuildAwareShopRerollPolicy.recommend
    original_reroll_joker_evaluate = RerollJokerExpectationEvaluator.evaluate

    def decide(self, state, visible_actions, *, reroll_cost):
        profile: dict[str, float | int] = {}
        token = _ACTIVE_PROFILE.set(profile)
        started = perf_counter()
        try:
            return original_decide(
                self,
                state,
                visible_actions,
                reroll_cost=reroll_cost,
            )
        finally:
            profile["total_seconds"] = perf_counter() - started
            _ACTIVE_PROFILE.reset(token)
            _LAST_PROFILE.set(profile)

    def rank_actions(self, state, actions):
        return _record_stage(
            "deterministic",
            original_rank_actions,
            self,
            state,
            actions,
        )

    def best_joker(self, state):
        return _record_stage("joker", original_best_joker, self, state)

    def best_consumable(self, state):
        return _record_stage("consumable", original_best_consumable, self, state)

    def best_bond_pair(self, state):
        return _record_stage("bond_pair", original_best_bond_pair, self, state)

    def booster_recommend(self, state, action):
        return _record_stage(
            "booster",
            original_booster_recommend,
            self,
            state,
            action,
        )

    def reroll_recommend(
        self,
        state,
        visible_actions,
        *,
        reroll_cost,
        visible_score_floor=None,
    ):
        return _record_stage(
            "reroll",
            original_reroll_recommend,
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
            visible_score_floor=visible_score_floor,
        )

    def reroll_joker_evaluate(self, state, *, money, expected_price):
        return _record_stage(
            "reroll_joker",
            original_reroll_joker_evaluate,
            self,
            state,
            money=money,
            expected_price=expected_price,
        )

    BuildAwareShopArbiter.decide = decide
    BalatroShopPolicy.rank_actions = rank_actions
    BuildAwareShopArbiter._best_joker_decision = best_joker
    BuildAwareShopArbiter._best_consumable_decision = best_consumable
    BuildAwareShopArbiter._best_visible_bond_pair = best_bond_pair
    BuildAwareShopBoosterPolicy.recommend = booster_recommend
    BuildAwareShopRerollPolicy.recommend = reroll_recommend
    RerollJokerExpectationEvaluator.evaluate = reroll_joker_evaluate
    BuildAwareShopArbiter._shop_policy_latency_diagnostic_installed = True


__all__ = [
    "clear_shop_policy_latency_profile",
    "consume_shop_policy_latency_note",
    "install_shop_policy_latency_diagnostic",
]
