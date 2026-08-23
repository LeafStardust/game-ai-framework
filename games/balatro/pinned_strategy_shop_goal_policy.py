from __future__ import annotations

"""Bounded D14 preference for acquisitions that satisfy pinned strategy goals.

D2 remains the admission authority. This layer only adds parent-shop value after a
Joker has already been admitted, so pinned strategy construction cannot bypass
legality, affordability, build-transition or replacement rules.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.shop_utility_scale import ShopUtilityScale


_MAX_GOAL_BONUS = 1.25
_PER_FEATURE_BONUS = 0.50


def _pinned_goals(state) -> tuple[str, ...]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()
    pinned_id = getattr(composition, "pinned_strategy_id", None)
    if not pinned_id:
        return ()
    for candidate in getattr(composition, "strategy_candidates", ()) or ():
        if candidate.strategy_id != pinned_id or not candidate.pinned:
            continue
        return tuple(
            prescription.split(":", 1)[1]
            for prescription in candidate.prescriptions
            if str(prescription).startswith("seek_feature:")
        )
    return ()


def _candidate_outputs(candidate) -> frozenset[str]:
    try:
        descriptor = ScenarioJokerBehaviorAnalyzer().describe(candidate)
    except (AttributeError, TypeError, ValueError):
        return frozenset()
    return frozenset(set(descriptor.produces) | set(descriptor.transforms))


def install_pinned_strategy_shop_goal_policy() -> None:
    if getattr(ShopUtilityScale, "_pinned_strategy_shop_goal_installed", False):
        return
    original = ShopUtilityScale.joker_gain

    def joker_gain(self, state, executable):
        utility = original(self, state, executable)
        candidate = getattr(executable, "candidate", None)
        if candidate is None:
            return utility
        goals = set(_pinned_goals(state))
        if not goals:
            return utility
        matched = sorted(goals.intersection(_candidate_outputs(candidate)))
        if not matched:
            return utility
        bonus = min(_MAX_GOAL_BONUS, _PER_FEATURE_BONUS * len(matched))
        return replace(
            utility,
            gain=float(utility.gain) + bonus,
            notes=(
                *utility.notes,
                f"pinned strategy unmet-feature bonus={bonus:.3f}",
                "matched pinned goals=" + ", ".join(matched),
                "D2 admission and D14 resource guards remain authoritative",
            ),
        )

    ShopUtilityScale.joker_gain = joker_gain
    ShopUtilityScale._pinned_strategy_shop_goal_installed = True
