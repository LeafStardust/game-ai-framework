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
_IN_REROLL_FUTURE: ContextVar[bool] = ContextVar(
    "balatro_shop_d11_in_reroll_future",
    default=False,
)

# These buckets are disjoint direct children of D14. ``deterministic`` is excluded
# because BalatroShopPolicy.rank_actions can also execute inside reroll evaluation;
# it remains visible as an overlapping informational metric. D11 substage buckets
# are likewise nested within ``reroll`` and are never subtracted from D14 residual.
_TOP_LEVEL_STAGES = (
    "joker_standalone",
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
    reroll_future = float(profile.get("reroll_future_seconds", 0.0))
    future_children = sum(
        float(profile.get(f"reroll_future_{family}_seconds", 0.0))
        for family in ("joker", "tarot", "planet")
    )
    future_residual = max(0.0, reroll_future - future_children)
    return (
        "shop_d14_latency="
        f"total={total:.3f}s "
        f"deterministic={float(profile.get('deterministic_seconds', 0.0)):.3f}s "
        f"joker_standalone={float(profile.get('joker_standalone_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('joker_standalone_calls', 0))}calls "
        f"joker={float(profile.get('joker_seconds', 0.0)):.3f}s "
        f"consumable={float(profile.get('consumable_seconds', 0.0)):.3f}s "
        f"booster={float(profile.get('booster_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('booster_calls', 0))}calls "
        f"bond_pair={float(profile.get('bond_pair_seconds', 0.0)):.3f}s "
        f"reroll={float(profile.get('reroll_seconds', 0.0)):.3f}s "
        f"reroll_visible={float(profile.get('reroll_visible_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_visible_calls', 0))}calls "
        f"reroll_unmet={float(profile.get('reroll_unmet_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_unmet_calls', 0))}calls "
        f"reroll_future={reroll_future:.3f}s/"
        f"{int(profile.get('reroll_future_calls', 0))}calls "
        f"reroll_future_joker={float(profile.get('reroll_future_joker_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_future_joker_calls', 0))}calls "
        f"reroll_future_tarot={float(profile.get('reroll_future_tarot_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_future_tarot_calls', 0))}calls "
        f"reroll_future_planet={float(profile.get('reroll_future_planet_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_future_planet_calls', 0))}calls "
        f"reroll_future_residual={future_residual:.3f}s "
        f"reroll_joker={float(profile.get('reroll_joker_seconds', 0.0)):.3f}s/"
        f"{int(profile.get('reroll_joker_calls', 0))}calls "
        f"residual={residual:.3f}s"
    )


def install_shop_policy_latency_diagnostic() -> None:
    if getattr(BuildAwareShopArbiter, "_shop_policy_latency_diagnostic_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide
    original_rank_actions = BalatroShopPolicy.rank_actions
    original_standalone_jokers = BuildAwareShopArbiter._standalone_joker_decisions
    original_best_joker = BuildAwareShopArbiter._best_joker_decision
    original_best_consumable = BuildAwareShopArbiter._best_consumable_decision
    original_best_bond_pair = BuildAwareShopArbiter._best_visible_bond_pair
    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend
    original_reroll_recommend = BuildAwareShopRerollPolicy.recommend
    original_reroll_visible = BuildAwareShopRerollPolicy._visible_scores
    original_reroll_unmet = BuildAwareShopRerollPolicy._unmet_requirements
    original_reroll_future = BuildAwareShopRerollPolicy._future_shop_ev
    original_reroll_offer_score = BuildAwareShopRerollPolicy._future_offer_score
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

    def best_joker(self, state, *, standalone=None):
        return _record_stage(
            "joker",
            original_best_joker,
            self,
            state,
            standalone=standalone,
        )

    def standalone_jokers(state, *, policy):
        return _record_stage(
            "joker_standalone",
            original_standalone_jokers,
            state,
            policy=policy,
        )

    def best_consumable(self, state):
        return _record_stage("consumable", original_best_consumable, self, state)

    def best_bond_pair(self, state, *, policy=None, standalone=None):
        return _record_stage(
            "bond_pair",
            original_best_bond_pair,
            self,
            state,
            policy=policy,
            standalone=standalone,
        )

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

    def reroll_visible(self, state, visible_actions):
        return _record_stage(
            "reroll_visible",
            original_reroll_visible,
            self,
            state,
            visible_actions,
        )

    def reroll_unmet(self, state):
        return _record_stage(
            "reroll_unmet",
            original_reroll_unmet,
            self,
            state,
        )

    def reroll_future(self, state, prior, *, money_after_reroll, thresholds):
        token = _IN_REROLL_FUTURE.set(True)
        try:
            return _record_stage(
                "reroll_future",
                original_reroll_future,
                self,
                state,
                prior,
                money_after_reroll=money_after_reroll,
                thresholds=thresholds,
            )
        finally:
            _IN_REROLL_FUTURE.reset(token)

    def reroll_offer_score(self, state, offer, *, money, thresholds):
        if not _IN_REROLL_FUTURE.get():
            return original_reroll_offer_score(
                self,
                state,
                offer,
                money=money,
                thresholds=thresholds,
            )
        family = str(getattr(offer, "family", "") or "").strip().lower()
        stage = (
            f"reroll_future_{family}"
            if family in {"joker", "tarot", "planet"}
            else "reroll_future_other"
        )
        return _record_stage(
            stage,
            original_reroll_offer_score,
            self,
            state,
            offer,
            money=money,
            thresholds=thresholds,
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
    BuildAwareShopArbiter._standalone_joker_decisions = staticmethod(
        standalone_jokers
    )
    BuildAwareShopArbiter._best_joker_decision = best_joker
    BuildAwareShopArbiter._best_consumable_decision = best_consumable
    BuildAwareShopArbiter._best_visible_bond_pair = best_bond_pair
    BuildAwareShopBoosterPolicy.recommend = booster_recommend
    BuildAwareShopRerollPolicy.recommend = reroll_recommend
    BuildAwareShopRerollPolicy._visible_scores = reroll_visible
    BuildAwareShopRerollPolicy._unmet_requirements = reroll_unmet
    BuildAwareShopRerollPolicy._future_shop_ev = reroll_future
    BuildAwareShopRerollPolicy._future_offer_score = reroll_offer_score
    RerollJokerExpectationEvaluator.evaluate = reroll_joker_evaluate
    BuildAwareShopArbiter._shop_policy_latency_diagnostic_installed = True


__all__ = [
    "clear_shop_policy_latency_profile",
    "consume_shop_policy_latency_note",
    "install_shop_policy_latency_diagnostic",
]
