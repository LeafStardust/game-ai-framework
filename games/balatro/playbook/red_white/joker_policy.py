from __future__ import annotations

from dataclasses import replace

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
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

    Canonical Bond/strategy transition value belongs to ``JokerAcquisitionPolicy``
    and is capped there. The Red/White cartridge supplies only its environment-owned
    D2 thresholds plus explicit mechanical conflict safety; it must not stack a
    second strategy-authority bonus above the universal Balatro D2 budget.
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

        # Pairwise mechanical safety is stronger than any current build preference.
        # A Burnt/Green/Burglar conflict may be resolved by a REPLACE that removes
        # the opposing Joker; it may never be admitted as a coexistence BUY or as a
        # replacement of some unrelated slot.
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
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "discard-mechanic conflict blocks coexistence: Burnt cannot share a build with Green Joker or Burglar",
                ),
            )

        return decision
