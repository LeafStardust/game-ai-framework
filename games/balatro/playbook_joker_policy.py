from __future__ import annotations

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.state import BalatroState


class PlaybookJokerAcquisitionPolicy:
    """Resolve D2 thresholds per state while reusing the canonical build evaluator.

    This adapter owns only deck/stake threshold lookup. It deliberately contains no
    legacy Gold/Silver/Bronze strategy-tier admission or replacement authority.
    Strategic direction belongs to the canonical Bond/composition system.
    """

    def __init__(self, transition_planner: JokerBuildTransitionPlanner) -> None:
        self.transition_planner = transition_planner

    def decide(
        self,
        state: BalatroState,
        candidate: object,
    ) -> JokerAcquisitionDecision:
        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            thresholds = JokerAcquisitionThresholds()
        else:
            thresholds = JokerAcquisitionThresholds.from_mapping(
                playbook.thresholds_for("D2")
            )

        return JokerAcquisitionPolicy(
            thresholds,
            transition_planner=self.transition_planner,
        ).decide(state, candidate)
