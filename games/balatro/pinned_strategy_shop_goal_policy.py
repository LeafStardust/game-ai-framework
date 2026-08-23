from __future__ import annotations

"""Bounded D14 preference for acquisitions that satisfy the applied strategy plan.

D2 remains the admission authority. This layer only adds parent-shop value after a
Joker has already been admitted, so strategy construction cannot bypass legality,
affordability, build-transition or replacement rules.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.shop_utility_scale import ShopUtilityScale


_MAX_GOAL_BONUS = 1.25
_PER_FEATURE_BONUS = 0.50
_MAX_TRACKED_BOND_GOALS = 3


_BOND_FEATURES: dict[str, tuple[str, ...]] = {
    "kings": ("rank:K",),
    "queens": ("rank:Q",),
    "jacks": ("rank:J",),
    "aces": ("rank:A",),
    "low_ranks": ("rank:2", "rank:3", "rank:4", "rank:5"),
    "hearts": ("suit:hearts",),
    "spades": ("suit:spades",),
    "clubs": ("suit:clubs",),
    "diamonds": ("suit:diamonds",),
    "steel": ("enhancement:steel", "held:effect"),
    "glass": ("enhancement:glass",),
    "lucky": ("enhancement:lucky",),
    "gold_economy": ("enhancement:gold", "economy"),
    "enhanced_cards": ("enhancement:steel", "enhancement:glass", "enhancement:gold"),
    "held_cards": ("held:effect",),
    "held_retrigger": ("held:retrigger",),
    "played_retrigger": ("played:retrigger",),
    "cash": ("economy",),
    "high_card": ("hand:high_card",),
    "pair": ("hand:pair",),
    "two_pair": ("hand:two_pair",),
    "three_kind": ("hand:three_of_a_kind",),
    "four_kind": ("hand:four_of_a_kind",),
    "straight": ("hand:straight",),
    "flush": ("hand:flush",),
    "full_house": ("hand:full_house",),
    "straight_flush": ("hand:straight_flush",),
    "five_kind": ("hand:five_of_a_kind",),
    "flush_house": ("hand:flush_house",),
    "flush_five": ("hand:flush_five",),
}


def _pinned_goals(state) -> tuple[str, ...]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()

    plan = getattr(composition, "strategy_plan", None)
    if plan is not None:
        goals: list[str] = list(getattr(plan, "missing_features", ()) or ())
        for bond_goal in tuple(getattr(plan, "bond_goals", ()) or ())[:_MAX_TRACKED_BOND_GOALS]:
            goals.extend(_BOND_FEATURES.get(str(bond_goal.bond_id), ()))
        return tuple(dict.fromkeys(goal for goal in goals if goal))

    # Compatibility fallback for synthetic/legacy Composition objects.
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
                f"applied strategy goal bonus={bonus:.3f}",
                "matched strategy goals=" + ", ".join(matched),
                "D2 admission and D14 resource guards remain authoritative",
            ),
        )

    ShopUtilityScale.joker_gain = joker_gain
    ShopUtilityScale._pinned_strategy_shop_goal_installed = True
