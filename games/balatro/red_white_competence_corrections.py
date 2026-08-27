from __future__ import annotations

"""Final Red/White competence corrections derived from live-run failures.

This layer is intentionally small and semantic. It does not predict hidden shop
contents or draw order. It corrects public-state mistakes observed in live
Red/White runs:

* conditional scoring mechanics discoverable from public rules could be omitted
  from representative shop score projection when their activation context was not
  present in the neutral probe state;
* shop Wheel of Fortune was never admitted by the deterministic D4 immediate-use
  path, even with healthy money and eligible editionless Jokers.

D1 multi-card redraw efficiency and discard-beam ranking now live in the canonical
D1 evaluator/planner path. Visible two-Joker Bond planning now lives directly in
D14. Paint Brush/Palette first-engine readiness now lives directly in D3, and the
early scoring foothold now lives directly in D2. This module remains installed only
for the two still-unconsolidated family-local corrections below.
"""

from copy import deepcopy
from dataclasses import replace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.build.joker_scenarios import (
    ScenarioJokerBehaviorAnalyzer,
    scenario_feature,
)
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.celestial_shop_headroom_fast_path import (
    install_celestial_shop_headroom_fast_path,
)
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    HOLD as CONSUMABLE_HOLD,
    ConsumableAcquisitionOption,
    ConsumableAcquisitionPolicy,
)


WHEEL_NAMES = frozenset({"The Wheel of Fortune", "Wheel of Fortune"})
REPEATED_HAND_SCENARIO = scenario_feature("repeated_hand")


_SCENARIO_ANALYZER = ScenarioJokerBehaviorAnalyzer()


def install_red_white_competence_corrections() -> None:
    install_celestial_shop_headroom_fast_path()
    if getattr(JokerBuildValueEvaluator, "_rw_competence_corrections_installed", False):
        return

    original_consumable_decide = ConsumableAcquisitionPolicy.decide
    original_direct_scoring_gain = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        base_gain = float(original_direct_scoring_gain(self, state, joker))
        try:
            descriptor = _SCENARIO_ANALYZER.describe(joker)
        except (AttributeError, TypeError, ValueError):
            return base_gain

        if REPEATED_HAND_SCENARIO not in set(getattr(descriptor, "requires", ()) or ()):
            return base_gain

        repeated_state = deepcopy(state)
        counts = dict(getattr(repeated_state, "round_hand_play_counts", {}) or {})
        for poker_hand, _ in self._scoring_probes(repeated_state):
            counts[poker_hand.value] = max(1, int(counts.get(poker_hand.value, 0) or 0))
        repeated_state.round_hand_play_counts = counts
        repeated_gain = float(original_direct_scoring_gain(self, repeated_state, joker))
        return (base_gain + repeated_gain) / 2.0

    def consumable_decide(self, state, candidate):
        decision = original_consumable_decide(self, state, candidate)
        if decision.action != CONSUMABLE_HOLD:
            return decision
        name = str(getattr(candidate, "name", type(candidate).__name__))
        if name not in WHEEL_NAMES or not isinstance(candidate, Consumable):
            return decision
        if not tuple(getattr(state, "jokers", ()) or ()):
            return decision

        economics = self._economics(state, candidate, occupy_slot=False)
        if economics.money_after < int(self.thresholds.reserve_target):
            return decision
        try:
            can_use = candidate.can_use(ConsumableContext(state=state))
        except (AttributeError, TypeError, ValueError):
            can_use = False
        if not can_use:
            return decision

        expectation = WheelOfFortuneExpectationEvaluator().evaluate(state)
        if not expectation.available or not expectation.complete:
            return decision
        expected_gain = float(expectation.expected_build_gain)
        if expected_gain <= 0.0:
            return decision
        total = expected_gain + economics.total_adjustment
        option = ConsumableAcquisitionOption(
            mode=BUY_AND_USE,
            build_gain=expected_gain,
            immediate_gain=0.0,
            total_advantage=total,
            economics=economics,
            eligible=True,
            executable_action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=candidate),
            rationale=(
                "shop Wheel admitted through the same public-state stochastic edition model used by packs",
                f"analytic expected edition gain={expected_gain:.3f}",
                f"money after purchase=${economics.money_after}",
                "D14 shared money/interest scale remains authoritative against END_SHOP",
                *tuple(expectation.rationale),
            ),
        )
        return replace(
            decision,
            action=BUY_AND_USE,
            selected=option,
            options=(option, *tuple(getattr(decision, "options", ()) or ())),
            rationale=(
                *tuple(getattr(decision, "rationale", ()) or ()),
                "eligible Wheel gets a direct BUY_AND_USE shop mode instead of deterministic-D4 rejection",
            ),
        )

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    ConsumableAcquisitionPolicy.decide = consumable_decide

    JokerBuildValueEvaluator._rw_competence_corrections_installed = True
    ConsumableAcquisitionPolicy._rw_competence_corrections_installed = True
