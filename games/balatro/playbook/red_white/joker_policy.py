from __future__ import annotations

from dataclasses import replace

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    BUY,
    HOLD,
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

        decision = JokerAcquisitionPolicy(
            thresholds,
            transition_planner=self.transition_planner,
        ).decide(state, candidate)

        # The generic D2 last-slot penalty represents the option value of keeping
        # one ordinary Joker slot open. Once the universal strategy is established,
        # that option value must not veto a positively valued Joker that is already
        # aligned with the active route. This is especially important for paired
        # scoring components (for example chips + mult Jokers for the same hand).
        # Price, interest and cash-reserve costs remain fully authoritative.
        if (
            decision.action == HOLD
            and len(state.jokers) < int(state.joker_slots)
            and decision.options
        ):
            transition = self.transition_planner.plan(state, candidate)
            candidate_value = transition.candidate_value
            aligned = bool(
                getattr(candidate_value, "active_alignment", False)
                and getattr(candidate_value, "strategy_tier", None)
                in {"GOLD", "SILVER", "BRONZE"}
            )
            option = decision.options[0]
            slot_adjusted_advantage = (
                float(option.total_advantage) + float(option.economics.slot_penalty)
            )
            if (
                aligned
                and option.eligible
                and slot_adjusted_advantage > thresholds.minimum_purchase_advantage
            ):
                return replace(
                    decision,
                    action=BUY,
                    selected=option,
                    rationale=(
                        *decision.rationale,
                        "active-strategy aligned Joker may consume the final free slot",
                        "final-slot opportunity penalty is waived for admission only; price/interest/reserve costs remain",
                        f"slot-adjusted buy advantage={slot_adjusted_advantage:.3f} exceeds threshold={thresholds.minimum_purchase_advantage:.3f}",
                    ),
                )

        return decision
