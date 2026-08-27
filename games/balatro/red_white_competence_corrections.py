from __future__ import annotations

"""Final Red/White competence correction retained for one scoring projection gap.

Conditional scoring mechanics discoverable from public rules can be omitted from
representative shop score projection when their activation context is absent from
the neutral probe state. All former D1, D2, D3, D4 and D14 rescue/arbitration
corrections have been migrated to their canonical owners.
"""

from copy import deepcopy

from games.balatro.build.joker_scenarios import (
    ScenarioJokerBehaviorAnalyzer,
    scenario_feature,
)
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.celestial_shop_headroom_fast_path import (
    install_celestial_shop_headroom_fast_path,
)


REPEATED_HAND_SCENARIO = scenario_feature("repeated_hand")
_SCENARIO_ANALYZER = ScenarioJokerBehaviorAnalyzer()


def install_red_white_competence_corrections() -> None:
    install_celestial_shop_headroom_fast_path()
    if getattr(JokerBuildValueEvaluator, "_rw_competence_corrections_installed", False):
        return

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

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    JokerBuildValueEvaluator._rw_competence_corrections_installed = True
