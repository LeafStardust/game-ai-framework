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
    """Resolve D2 thresholds per state while reusing one run-scoped B3 evaluator.

    The transition planner owns the shared build-value evaluator and its persistent
    playstyle-intent tracker. Only D2 thresholds are reconstructed from the active
    deck/stake playbook for each authoritative shop observation.
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
