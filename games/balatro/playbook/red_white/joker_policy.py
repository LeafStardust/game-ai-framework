from __future__ import annotations

from dataclasses import replace

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.state import BalatroState


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(character for character in str(value).lower() if character.isalnum())


def _discard_conflict_indices(state: BalatroState, candidate: object) -> tuple[int, ...]:
    """Return owned slots mechanically incompatible with this candidate.

    Burnt needs the first discard. Green loses Mult on every discard; Burglar removes
    all discards. Green and Burglar are intentionally compatible with each other.
    """
    candidate_token = _joker_token(candidate)
    burnt = {"burnt", "burntjoker"}
    green = {"green", "greenjoker"}
    burglar = {"burglar", "burglarjoker"}

    if candidate_token in burnt:
        opposing = green | burglar
    elif candidate_token in green | burglar:
        opposing = burnt
    else:
        return ()

    return tuple(
        index
        for index, joker in enumerate(getattr(state, "jokers", ()) or ())
        if _joker_token(joker) in opposing
    )


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

        # Pairwise mechanic safety is stronger than whichever poker-hand route is
        # currently Primary. A Burnt/Green/Burglar conflict may be resolved by a
        # REPLACE that removes the opposing Joker; it may never be admitted as a
        # coexistence BUY or as a replacement of some unrelated slot.
        conflict_indices = _discard_conflict_indices(state, candidate)
        if conflict_indices:
            if decision.action == REPLACE and getattr(decision, "selected", None) is not None:
                try:
                    replace_index = int(decision.selected.replace_index)
                except (AttributeError, TypeError, ValueError):
                    replace_index = -1
                if replace_index in conflict_indices:
                    return replace(
                        decision,
                        rationale=(
                            *decision.rationale,
                            "discard-mechanic conflict resolved by replacing the opposing Burnt/Green/Burglar component",
                        ),
                    )

            if decision.action != HOLD:
                return replace(
                    decision,
                    action=HOLD,
                    selected=None,
                    rationale=(
                        *decision.rationale,
                        "mechanical conflict: Burnt requires a discard while Green punishes discards and Burglar removes them",
                        "candidate may only enter by replacing the opposing discard/no-discard component",
                    ),
                )

            # Preserve an existing HOLD and prevent the final-slot alignment waiver
            # below from resurrecting the contradictory candidate as a BUY.
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "mechanical conflict retained: Burnt and Green/Burglar cannot coexist",
                ),
            )

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