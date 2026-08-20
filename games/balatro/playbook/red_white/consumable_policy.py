from __future__ import annotations

from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.shop_consumable_policy import (
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)


class PlaybookConsumableAcquisitionPolicy:
    """Resolve D4 thresholds per state while reusing one strategy-aware evaluator."""

    def __init__(self, *, evaluator, timing_policy) -> None:
        self.evaluator = evaluator
        self.timing_policy = timing_policy

    def decide(self, state, candidate):
        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            thresholds = ConsumableAcquisitionThresholds()
        else:
            thresholds = ConsumableAcquisitionThresholds.from_mapping(
                playbook.thresholds_for("D4")
            )
        return ConsumableAcquisitionPolicy(
            thresholds,
            evaluator=self.evaluator,
            timing_policy=self.timing_policy,
        ).decide(state, candidate)
